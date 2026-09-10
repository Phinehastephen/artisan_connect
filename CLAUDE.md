# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Artisan Connect is a Django REST API backend for a location-based artisan marketplace (final-year project, MVP-first). It connects customers with verified artisans (electricians, plumbers, etc.) via services, bookings, reviews, and location-based discovery. Full product vision, roadmap, and business rules live in [README.md](README.md) — read it for context on *why* a rule exists before changing business logic.

Key non-obvious project conventions from the README worth internalizing:
- **Frozen tables**: once a table/module is approved, it isn't casually redesigned. Check the README's "Important Architecture Decisions" section before changing model shapes.
- Phone numbers are private (never exposed via API to other users); usernames are editable; multiple active sessions per user are supported by design.
- Labour price estimation (planned AI feature) excludes material costs — a deliberate scope boundary, not an oversight.

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

**Identity model**: `accounts.User` (custom `AUTH_USER_MODEL`, `AbstractUser` subclass) carries a `role` field (`CUSTOMER` / `ARTISAN` / `ADMIN`). Registering a customer or artisan creates both the `User` row and a matching `customers.Customer` / `artisans.Artisan` profile row in one atomic call (`accounts/services.py`) — there is no separate "create profile" step. `Artisan` and `Customer` are OneToOne with `User`.

**Cross-app foreign keys**: `bookings.Booking` is the hub connecting `customers.Customer`, `artisans.Artisan`, and `services.Service` (all `on_delete=PROTECT`, so historical bookings block deleting a referenced customer/artisan/service). `reviews.Review` is OneToOne with `Booking` — a booking can have at most one review, and only after `Booking.status == COMPLETED`.

**State machines**: `Booking.status` moves `PENDING → ACCEPTED → IN_PROGRESS → COMPLETED → FINALIZED` (or `CANCELLED`), enforced by one function per transition in `bookings/services.py` (`accept_booking`, `start_booking`, `complete_booking`, `finalize_booking`), each checking the current status before transitioning. `finalize_booking` also strips `job_address`/`job_latitude`/`job_longitude` for privacy once a job is closed out. `views.py` dispatches these via an `action_map` keyed by a URL path segment (`status/<pk>/<action>`), not separate endpoints per action — the same pattern is used for artisan verification (`verification/<pk>/<action>` with `approve`/`reject`).

**Quota-style invariants enforced in `services.py`, not at the model/DB layer**:
- An artisan may offer at most 3 services (`artisans/services.py: MAX_ARTISAN_SERVICES`), also re-validated at registration time in `accounts/serializers.py`.
- A customer may have at most 5 saved locations (`locations/services.py: MAX_SAVED_LOCATIONS`).
- A review can be edited exactly once, only by the reviewing customer, only within 24 hours of creation (`reviews/services.py: edit_review`).

**Auth**: JWT via `djangorestframework-simplejwt` (`rest_framework_simplejwt`), configured as the default DRF authentication class in `config/settings.py`. Login is a custom `CustomLoginSerializer`/`CustomJWTLoginView` (not simplejwt's built-in token view) so the response can be shaped with extra user fields; token refresh uses stock `TokenRefreshView`. There is no global `IsAuthenticated` default — each view sets `permission_classes` explicitly, so a missing/wrong `permission_classes` on a new view silently defaults to open access.
