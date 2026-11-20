from dataclasses import dataclass, field
from difflib import SequenceMatcher

from services.models import Service
from services.text import normalize_text

from .models import SearchLog


# Words that say nothing about which trade is needed. A query made only of
# these ("I need help with something") can't be matched to a service.
GENERIC_WORDS = {
    "a", "about", "am", "an", "and", "any", "anyone", "are", "at", "be",
    "can", "come", "could", "do", "does", "done", "for", "fix", "fixed",
    "fixing", "from", "get", "getting", "good", "have", "help", "hello",
    "hi", "home", "house", "how", "i", "im", "in", "is", "it", "job",
    "looking", "me", "my", "near", "need", "needed", "needs", "now", "of",
    "on", "or", "our", "person", "please", "pls", "problem", "repair",
    "repairs", "service", "services", "someone", "something", "soon",
    "the", "there", "this", "to", "today", "urgent", "urgently", "want",
    "we", "what", "who", "will", "with", "work", "would", "you", "your",
}

# Score weights. A multi-word keyword ("leaking pipe") is more specific than
# a single word, and a typo-match counts for less than an exact word.
PHRASE_WEIGHT = 2.0
WORD_WEIGHT = 1.0
CLOSE_TYPO_WEIGHT = 1.0
LOOSE_TYPO_WEIGHT = 0.6

CLOSE_TYPO_RATIO = 0.9
LOOSE_TYPO_RATIO = 0.8
MIN_TYPO_LENGTH = 4

# Confident only when one service has at least one solid word match and
# beats the runner-up by at least one more.
CONFIDENT_MIN_SCORE = 1.0
CONFIDENT_MIN_LEAD = 1.0
MAX_SUGGESTIONS = 3

# Anything wrong with a vehicle is a mechanic's job, even when it also names
# another trade's keyword ("car ac", "car wiring", "car battery").
VEHICLE_SERVICE_NAME = "Auto Repair"
VEHICLE_WORDS = {
    "car", "cars", "vehicle", "vehicles", "truck", "lorry", "bus", "van",
    "jeep", "suv", "keke", "tricycle", "motorcycle", "motorbike", "okada",
}

_SUFFIXES = ("ings", "ing", "ers", "er", "ians", "ian", "ies", "es", "ed", "s")


def _stem(word):

    for suffix in _SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    return word


@dataclass
class SearchResult:
    confidence: str
    service: Service | None = None
    suggestions: list = field(default_factory=list)


def _service_vocabulary():
    # Every active service with its name and keywords, normalized.
    vocabulary = []
    for service in Service.objects.filter(is_active=True).prefetch_related("keywords"):
        name = normalize_text(service.name)
        terms = {name}
        # Each word of a multi-word name counts alone too: "auto" -> Auto Repair.
        terms.update(word for word in name.split() if word not in GENERIC_WORDS)
        terms.update(keyword.keyword for keyword in service.keywords.all())
        vocabulary.append((service, {term for term in terms if term}))
    return vocabulary


def _score(words, query, terms, typo_words):
    score = 0.0
    stems = {_stem(word) for word in words}
    typo_stems = {_stem(word) for word in typo_words}
    padded_query = f" {query} "

    for term in terms:
        term_words = term.split()

        if len(term_words) > 1:
            if f" {term} " in padded_query:
                score += PHRASE_WEIGHT
            continue

        term_stem = _stem(term)
        if term_stem in stems:
            score += WORD_WEIGHT
            continue

        if len(term_stem) < MIN_TYPO_LENGTH:
            continue

        # Check for typos. checking both the stemmed and unstemmed versions of the word, and take the best match.
        stem_ratio = max(
            (
                SequenceMatcher(None, stem, term_stem).ratio()
                for stem in typo_stems
                if len(stem) >= MIN_TYPO_LENGTH
            ),
            default=0,
        )
        word_ratio = max(
            (
                SequenceMatcher(None, word, term).ratio()
                for word in typo_words
                if len(word) >= MIN_TYPO_LENGTH
            ),
            default=0,
        )
        if word_ratio < CLOSE_TYPO_RATIO:
            word_ratio = 0
        best_ratio = max(stem_ratio, word_ratio)
        if best_ratio >= CLOSE_TYPO_RATIO:
            score += CLOSE_TYPO_WEIGHT
        elif best_ratio >= LOOSE_TYPO_RATIO:
            score += LOOSE_TYPO_WEIGHT

    return score


def match_service(query):
    query = normalize_text(query)
    words = [word for word in query.split() if word not in GENERIC_WORDS]

    if not words:
        return SearchResult(SearchLog.Confidence.NONE)

    vocabulary = _service_vocabulary()

    for service, _terms in vocabulary:
        if normalize_text(service.name) == query:
            return SearchResult(SearchLog.Confidence.CONFIDENT, service=service)

    if VEHICLE_WORDS.intersection(words):
        for service, _terms in vocabulary:
            if service.name == VEHICLE_SERVICE_NAME:
                return SearchResult(SearchLog.Confidence.CONFIDENT, service=service)

    known_stems = {
        _stem(term)
        for _service, terms in vocabulary
        for term in terms
        if " " not in term
    }
    typo_words = [word for word in words if _stem(word) not in known_stems]

    scored = sorted(
        ((_score(words, query, terms, typo_words), service) for service, terms in vocabulary),
        key=lambda pair: (-pair[0], pair[1].name),
    )
    scored = [(score, service) for score, service in scored if score > 0]

    if not scored:
        return SearchResult(SearchLog.Confidence.NONE)

    best_score, best_service = scored[0]
    runner_up = scored[1][0] if len(scored) > 1 else 0.0

    if best_score >= CONFIDENT_MIN_SCORE and best_score - runner_up >= CONFIDENT_MIN_LEAD:
        return SearchResult(SearchLog.Confidence.CONFIDENT, service=best_service)

    return SearchResult(
        SearchLog.Confidence.UNSURE,
        suggestions=[service for _score_value, service in scored[:MAX_SUGGESTIONS]],
    )


def log_search(customer, query, result):
    return SearchLog.objects.create(
        customer=customer,
        query=query[:200],
        matched_service=result.service,
        confidence=result.confidence,
    )
