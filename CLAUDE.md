# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Artisan Connect is a Django REST API backend for a location-based artisan marketplace (final-year project, MVP-first). It connects customers with verified artisans (electricians, plumbers, etc.) via services, bookings, reviews, and location-based discovery. Full product vision, roadmap, and business rules live in [README.md](README.md) — read it for context on _why_ a rule exists before changing business logic.

Key non-obvious project conventions from the README worth internalizing:

- **Frozen tables**: once a table/module is approved, it isn't casually redesigned. Check the README's "Important Architecture Decisions" section before changing model shapes.
- Phone numbers are private (never exposed via API to other users); usernames are editable; multiple active sessions per user are supported by design.
- Labour price estimation (planned AI feature) excludes material costs — a deliberate scope boundary, not an oversight.
- **Service Change Request (planned, not yet implemented)**: an artisan's `services` M2M is meant to be editable only through a reviewed request flow, not a direct profile edit, once the initial 1–3 services are set at registration. Flow: artisan submits a request with a reason → admin approves/rejects → on approval, services update and the artisan enters a 12-month cooldown before requesting again. See README's "Service Change Requests" section. There is currently no `ServiceChangeRequest` model, service function, or endpoint — don't assume one exists, and route any future implementation through `artisans/services.py` per the layering rule below rather than letting `ArtisanProfileUpdateSerializer`/`update_artisan_profile` touch `services` directly.

## Recent validation summary

The project has been validated with end-to-end Django simulations in the real app environment, including the full booking workflow and the map-based nearby-artisan flow.

Verified behaviors:

- natural-language smart search resolves to a likely service
- `current` and `saved` location modes both resolve to usable coordinates
- nearby-artisan discovery returns only verified artisans within range
- a temporary customer can create a booking, accept it, start it, complete it, and finalize it
- a disputed booking can move `COMPLETED -> DISPUTED -> FINALIZED`
- the dedicated nearby-artisan regression test passes: `locations.tests.MapNearbyArtisanFlowTests`

## Commands

Config is loaded from a `.env` file at the repo root (`SECRET_KEY`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`). The project uses PostgreSQL — there is no sqlite fallback in settings despite `db.sqlite3` being present in the repo.

```bash
# Run the dev server
python manage.py runserver

# Migrations
python manage.py makemigrations
python manage.py migrate

# Run all tests
python manage.py test

# Run tests for one app
python manage.py test artisans

# Run a single test case / method
python manage.py test artisans.tests.ArtisanBusinessLogicTests
python manage.py test artisans.tests.ArtisanBusinessLogicTests.test_artisan_cannot_have_four_services

# Django shell
python manage.py shell
```

There is no linter or formatter configured in this repo.

## Architecture

Each domain lives in its own Django app: `accounts`, `customers`, `artisans`, `services`, `bookings`, `reviews`, `locations`. All are wired under `config/` (settings, root urlconf). URLs are namespaced per app under `/api/v1/<app>/` in [config/urls.py](config/urls.py).

**Layering used consistently across every app** — read this before adding logic anywhere:

```
views.py (APIView)  →  serializers.py (validation/shape)  →  services.py (business rules, @transaction.atomic)  →  models.py
```

- `views.py` never contains business rules — it parses the request via a serializer, delegates to a function in `services.py`, and translates the result/`ValidationError` into an HTTP `Response`.
- `services.py` holds the actual business logic (state transitions, quota checks, authorization-adjacent invariants) as plain functions wrapped in `@transaction.atomic`, raising `django.core.exceptions.ValidationError` on rule violations. This is the layer to check/extend when a "business rule" needs to change.
- Serializers' `create()`/`update()` often just delegate to a `services.py` function rather than doing `Model.objects.create(**validated_data)` directly (see `accounts/serializers.py` calling `register_customer`/`register_artisan`).

**Identity model**: `accounts.User` (custom `AUTH_USER_MODEL`, `AbstractUser` subclass) carries a `role` field (`CUSTOMER` / `ARTISAN` / `ADMIN`). `createsuperuser` sets `role=ADMIN` (custom `UserManager`), and `User.save()` lowercases the email on every path. `IsCustomer`/`IsArtisan` require the matching profile row as well as the role, so a role-only user (e.g. made in Django admin) gets a 403 rather than a 500 — create customers/artisans through registration (the Django admin add-user form only offers the ADMIN role for that reason). `User.clean()` lowercases the email so the admin form's unique check catches case-variant duplicates. Usernames are unique case-insensitively at registration and on customer rename; artisans can't change their username. Registering a customer or artisan creates both the `User` row and a matching `customers.Customer` / `artisans.Artisan` profile row in one atomic call (`accounts/services.py`) — there is no separate "create profile" step. `Artisan` and `Customer` are OneToOne with `User`.

**Cross-app foreign keys**: `bookings.Booking` is the hub connecting `customers.Customer`, `artisans.Artisan`, and `services.Service` (all `on_delete=PROTECT`, so historical bookings block deleting a referenced customer/artisan/service). `reviews.Review` is OneToOne with `Booking` — a booking can have at most one review, and only once the booking is COMPLETED, DISPUTED or FINALIZED.

**State machines**: `Booking.status` moves `PENDING → ACCEPTED → IN_PROGRESS → COMPLETED → FINALIZED` (or `CANCELLED`), enforced by one function per transition in `bookings/services.py` (`accept_booking`, `start_booking`, `complete_booking`, `reject_booking`, `cancel_booking`, `confirm_completion`, `finalize_booking`). Each calls `_lock(booking)` first (row lock + `refresh_from_db`) so concurrent transitions can't both pass their status check — keep that in any new transition. Cancel is allowed from PENDING or ACCEPTED. Completion is two-party: the artisan's `complete` counts as their confirmation, the customer's `confirm` (action `confirm`) finalizes it; the customer can instead `disagree` (body `{"reason": ...}`, min `MIN_DISPUTE_REASON_LENGTH`=20 chars, checked in `dispute_completion`) → DISPUTED, which reminders/auto-finalize ignore because they only select COMPLETED. On a successful dispute, `send_dispute_notification` emails every active ADMIN user after commit via `accounts.services.run_in_background` (failures logged, never raised). Admin-only actions: `finalize` (from COMPLETED or DISPUTED) and `reopen` (DISPUTED → IN_PROGRESS, keeps `dispute_reason`, clears `completed_at`; the next `complete` resets `confirmation_reminders_sent` so the customer gets fresh reminders and a fresh 72h window). `dispute_reason` is on `BookingSerializer` (parties + admin only), never on `BookingSummarySerializer`. Every route to FINALIZED goes through `_finalize`, which sets `finalization_method` (CUSTOMER_CONFIRMED / AUTO / ADMIN) and strips `job_address`/`job_latitude`/`job_longitude`. `python manage.py process_completed_bookings` (meant to run hourly) sends customer reminder emails per `CONFIRMATION_REMINDER_SCHEDULE` (24h/48h/66h, counted in `confirmation_reminders_sent`, only incremented on a successful send) and auto-finalizes after `AUTO_FINALIZE_AFTER` (72h). Reviews are allowed on COMPLETED, DISPUTED or FINALIZED bookings. Bookings are created via `BookingCreateSerializer` (artisan, service, job_address, job_latitude, job_longitude all required) with `customer=request.user.customer_profile`; `BookingSerializer` is output-only. `views.py` dispatches these via an `action_map` keyed by a URL path segment (`status/<pk>/<action>`), not separate endpoints per action — the same pattern is used for artisan verification (`verification/<pk>/<action>` with `approve`/`reject`).

**Quota-style invariants enforced in `services.py`, not at the model/DB layer**:

- An artisan may offer at most 3 services (`artisans/services.py: MAX_ARTISAN_SERVICES`), also re-validated at registration time in `accounts/serializers.py` (which only offers active services) and in `ArtisanAdminForm`. Changing a service's prices (`services/services.py: update_service`, or `ServiceAdmin.save_model`) recalculates every linked artisan's range via `recalculate_price_ranges_for_service`; the artisan admin shows prices and `verification_status` read-only and verifies through `approve_artisan`/`reject_artisan` admin actions. Those two services enforce the PENDING-only rule themselves under a row lock.
- A customer may have at most 5 saved locations (`locations/services.py: MAX_SAVED_LOCATIONS`). `create_saved_location` locks the `Customer` row with `select_for_update()` before counting so concurrent requests can't overshoot the limit — keep that lock (and the `@transaction.atomic`) if you touch this function. The same pattern applies to any other count-then-insert quota.
- A review can be edited exactly once, only by the reviewing customer, only within 24 hours of creation (`reviews/services.py: edit_review`). The reviewing customer passed to `create_review`/`edit_review` must always be `request.user.customer_profile` — `customer`/`artisan` are read-only on `ReviewSerializer` and edits go through `ReviewEditSerializer` (rating/comment only), so a client can't act as another customer by putting their id in the request body.

**Artisan profile updates** (`artisans/services.py: update_artisan_profile`, backing `ArtisanMyProfileView.patch`) — established while implementing the endpoint, not part of the original spec:

- Only a `VERIFIED` artisan may update any profile field; `PENDING`/`REJECTED` artisans get a `ValidationError`. (They're also blocked at login in `CustomLoginSerializer` — an approved decision — so this check is a safety net.)
- `full_name` (on `User`), `profile_picture` (on `User`), and `business_name` (on `Artisan`) each have their own independent 6-month cooldown, tracked via a matching `*_updated_at` timestamp field. Re-sending an unchanged value is dropped before the cooldown check, so it neither errors nor restarts the cooldown. `phone_number` and `default_location` have no cooldown.
- `starting_price`/`maximum_price` on `Artisan` are never accepted as input anywhere — they're recalculated by `recalculate_artisan_price_range` (min/max across assigned `services`) whenever an artisan's services change (`register_artisan`, `ArtisanAdmin.save_related`, `add_service_to_artisan`) and whenever a service's prices or active flag change (`update_service`, `ServiceAdmin.save_model`). Only _active_ services count toward the range. `add_service_to_artisan` has no API caller yet — it's the building block for the planned Service Change Request flow. Treat prices as derived/read-only in any new code path that touches services.

**Phone number privacy is enforced via serializer choice, not a single field flag**: `artisans.ArtisanSerializer`/`customers.CustomerSerializer` include `phone_number` and are only for the profile owner's own view (`ArtisanMyProfileView`, `CustomerDetailView`) and admin-only views (`ArtisanVerificationAPIView`, `Pending`/`RejectedArtisanListAPIView`). Anywhere a customer and artisan can see _each other_ — the public marketplace listing (`ArtisanListView`), and the nested `customer_detail`/`artisan_detail` on `BookingSerializer` and `ReviewSerializer` — must use `ArtisanPublicSerializer`/`CustomerPublicSerializer` instead, which omit `phone_number` entirely. When adding any new place that serializes an `Artisan`/`Customer` for someone other than themselves or an admin, use the `*PublicSerializer`, not the full one.

**The goal behind this is preventing off-platform contact** (customer and artisan taking the job outside the app), so it covers more than phone numbers:

- The `*PublicSerializer`s nest `accounts.UserPublicSerializer` (no `email`, no `username`), not `UserSerializer`. `CustomerPublicSerializer` also omits the customer's `default_location`.
- `BookingSerializer.to_representation` nulls `job_address`/`job_latitude`/`job_longitude` unless the viewer is the booking's customer, an admin, or the booking's artisan while `status` is `ACCEPTED`/`IN_PROGRESS`. It reads the viewer from `context["request"]` and hides the location when there's no request — so always pass `context={"request": request}` when using it in a view.
- `ReviewSerializer` (readable by any authenticated user) nests `BookingSummarySerializer`, never `BookingSerializer`, so reviews can't leak a job location; the summary also omits `status` so a dispute isn't public.
- `reject_booking`, `cancel_booking` and `finalize_booking` all erase the job location in the DB via `_clear_job_location`.

**Booking list/detail are ownership-scoped, not just permission-gated**: `BookingListAPIView.get` filters by `request.user.role` (customer → own bookings via `customer__user`, artisan → own via `artisan__user`, admin → all); `BookingDetailView.get` checks `IsBookingCustomer`/`IsBookingArtisan`/admin before returning a booking fetched by raw pk. Any new booking-reading endpoint needs the same scoping — `Booking.objects.all()`/`.get(pk=pk)` alone is not sufficient, `permission_classes = [IsAuthenticated]` does not restrict _which_ bookings are visible.

**Customer profile updates** (`customers/services.py: update_customer_profile`, backing `CustomerDetailView.patch`): username, full_name, profile_picture (on `User`) and default_location (on `Customer`), no cooldowns (unlike artisans). `phone_number` and `email` are locked — `CustomerProfileUpdateSerializer` returns a 400 if they're sent instead of ignoring them. Username uniqueness is checked case-insensitively.

**Nearby-artisan search** (`locations/views.py: NearbyArtisanListView`, `GET /api/v1/locations/nearby-artisans`) accepts two modes: `?latitude=&longitude=` (or explicitly `location_type=current`, the default) and `?location_type=saved&location_id=<id>`. Query params are validated by `NearbyArtisanQuerySerializer`; `locations/services.py: resolve_search_coordinates` turns them into coordinates. The saved lookup must stay scoped to `customer=user.customer_profile` — another customer's `location_id` returns 404 (same as a nonexistent one) so saved locations can't be probed by ID; non-customers get a 400 for `saved`. The response is `{"origin": {latitude, longitude}, "results": [...]}` where each result is a map marker from `NearbyArtisanMarkerSerializer` (id, name, is_verified, distance_km, location, rounded latitude/longitude, average_rating, review_count, starting/maximum_price) — not the full `ArtisanPublicSerializer`. Marker coordinates are rounded to `MAP_COORDINATE_DECIMALS` (3, ~110 m) because an artisan's location may be their home. Don't add contact or identity fields (phone, email, username) to markers. `distance_km` is measured to the _rounded_ coordinates (`MAP_COORDINATE_DECIMALS` lives in `locations/services.py`) — measuring to the exact ones would let repeated searches triangulate the artisan's exact location. The view is customer-only (`IsCustomer`) and throttled (`nearby_search` scope).

**Geocoding** (`locations/services.py: geocode_address`/`reverse_geocode`, endpoints `locations/geocode` and `locations/reverse-geocode`) calls OpenStreetMap Nominatim over stdlib `urllib`. Every call must go through `_nominatim_get`, which enforces Nominatim's usage policy (≤1 request/second per process via a lock, identifying `NOMINATIM_USER_AGENT`); results are cached 24h in Django's cache, and the endpoints use the `geocoding` throttle scope. Network failures raise `GeocodingUnavailable` → 503. Tests must mock `locations.services.urlopen` (and patch `NOMINATIM_MIN_INTERVAL_SECONDS` to 0) — the suite should never hit the real service. Both directions honour `NOMINATIM_COUNTRY_CODES` (reverse results from another country are treated as "no address"). Coordinates in requests use `locations.serializers.CoordinateField`, which rounds extra GPS decimals to 6 instead of rejecting. Config: `NOMINATIM_BASE_URL`, `NOMINATIM_USER_AGENT`, `NOMINATIM_COUNTRY_CODES` (default `ng`), `NOMINATIM_TIMEOUT`.

**Smart Search** (`ai` app, `GET /api/v1/ai/search`, `ai/services.py: match_service`): rule-based V1 matcher, no ML libraries. Pipeline: `services.text.normalize_text` → reject queries made only of `GENERIC_WORDS` → exact `Service.name` → score each _active_ service's name (plus each non-generic word of a multi-word name, so "auto" → Auto Repair) + `ServiceKeyword`s (multi-word phrase 2.0, word 1.0 with light `_stem` so leaking/leak and plumber/plumbing match, typo via `difflib` stem ratio ≥0.8/0.9 or full-word ratio ≥0.9; only query words that aren't a known keyword of _any_ service are typo-matched, so "switch" can't count as a typo of "stitch"). → CONFIDENT if best ≥1 and leads runner-up by ≥1, else UNSURE (top 3), else NONE. Keep keywords free of `GENERIC_WORDS`; tune via `ServiceKeyword` rows in admin rather than code where possible. `SmartSearchView` (customers only, `smart_search` throttle) resolves location with the same `resolve_search_coordinates` as nearby search, logs every search to `ai.SearchLog` (customer, query, matched service, confidence; purged after 12 months by `purge_search_logs`), and on CONFIDENT calls `find_nearby_artisans(..., service=...)`. `locations.services.rank_artisans` is the single ranking step (distance for now) — the recommendation engine should replace it there. `ServiceKeyword.save()` normalizes the keyword; the English starter set is seeded by data migrations `services/0004_seed_service_keywords` and `0005_plumbing_water_keywords`, and `0006_masonry_generator_ac_services` creates the Masonry, Generator Repair and AC & Refrigeration services (with starting labour price ranges) plus their keywords. The keyword admin inline normalizes keywords in its form (`ServiceKeywordForm`) so case-variant duplicates are form errors, not IntegrityErrors.

**Email verification** (`accounts/models.py: EmailVerificationToken`, `accounts/services.py: create_email_verification_token`/`send_verification_email`/`verify_email`): non-blocking — never gates login or any feature, see README. A token (24h expiry, single-use via `used_at`) is created and its email queued via `transaction.on_commit(...)` inside `register_customer`/`register_artisan`, so the email only sends after the registration transaction actually commits, and a delivery failure (caught and logged in `send_verification_email`) never turns a successful registration into an API error. Requesting a new token invalidates any prior unused one for that user. Sent through Brevo's SMTP relay — `EMAIL_HOST`/`EMAIL_HOST_USER`/`EMAIL_HOST_PASSWORD`/`DEFAULT_FROM_EMAIL`/`BACKEND_BASE_URL` come from `.env`; `EMAIL_BACKEND` defaults to the console backend so local dev doesn't need real credentials. When testing code that goes through `register_customer`/`register_artisan` and asserting on the sent email, wrap the call in `self.captureOnCommitCallbacks(execute=True)` — plain `TestCase` rolls back instead of committing, so `on_commit` callbacks never fire otherwise.

**Password reset** (`accounts/models.py: PasswordResetToken`, `accounts/services.py: request_password_reset`/`verify_password_reset_code`/`reset_password`, endpoints `password-reset/request|verify|confirm`): a three-step OTP flow. `request` emails a 6-digit code (10-min expiry, stored hashed via `make_password`) and always returns the same response whether or not the email exists — don't add a "no such account" error, it would enable email enumeration. `verify` allows at most `PASSWORD_RESET_MAX_ATTEMPTS` (5) wrong guesses per code and on success returns a single-use `reset_token` (15-min window); `verify_password_reset_code` deliberately uses an inner `transaction.atomic()` block and raises _outside_ it so a failed attempt's counter increment isn't rolled back — don't convert it to a plain `@transaction.atomic` decorator. `confirm` runs Django's password validators against the user, sets the password, marks `email_verified=True` (receiving the code proves inbox control), and emails a "password changed" notice. `reset_password` blacklists every `OutstandingToken` for the user (simplejwt `token_blacklist` app, `BLACKLIST_AFTER_ROTATION=True`), so all refresh tokens die immediately; access tokens live out their 60-minute lifetime. To keep response time identical for registered and unknown emails, `request_password_reset` always hashes a code and sends the email via `run_in_background` — tests must use `@override_settings(SEND_EMAIL_IN_BACKGROUND=False)` (plus `captureOnCommitCallbacks`) to assert on `mail.outbox`. Request/verify endpoints are rate-limited via `ScopedRateThrottle` scopes in `REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']`.

**Auth**: JWT via `djangorestframework-simplejwt` (`rest_framework_simplejwt`), configured as the default DRF authentication class in `config/settings.py`. Login is a custom `CustomLoginSerializer`/`CustomJWTLoginView` (not simplejwt's built-in token view) so the response can be shaped with extra user fields; token refresh uses stock `TokenRefreshView`. Login (`login` scope, 10/min per IP) and registration (`registration` scope, 10/hour per IP) are throttled; registration runs Django's password validators against a draft user (so the similarity check applies, matching reset) and turns a username/email race (`IntegrityError`) into a 400. There is no global `IsAuthenticated` default — each view sets `permission_classes` explicitly, so a missing/wrong `permission_classes` on a new view silently defaults to open access.
