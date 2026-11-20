import re

_NOT_WORD = re.compile(r"[^a-z0-9]+")


def normalize_text(text):
    # Shared by stored keywords and search queries so both are compared in
    # the same form: "Leaking-Pipe!!" -> "leaking pipe".
    return " ".join(_NOT_WORD.sub(" ", (text or "").lower()).split())
