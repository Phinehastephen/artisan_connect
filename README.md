# Artisan Connect

> A location-based artisan marketplace that connects customers with nearby, verified artisans through a structured REST backend, location services, and intelligent search/recommendation features.

## 📌 Overview

Artisan Connect is a final-year project designed to solve the difficulty of finding reliable artisans such as electricians, plumbers, mechanics, cleaners, tailors, and other service providers.

The platform is being developed first as a practical MVP, with an architecture that can evolve into a commercial platform.

The project follows a **MVP-first, documentation-first, modular development approach**. Approved decisions are treated as the project's source of truth, and approved/frozen structures are not changed casually.

---

## 🎯 Vision

Build a reliable artisan marketplace that makes it easier for customers to:

- Find artisans based on the service they need.
- Discover nearby artisans using location.
- Identify verified and trustworthy artisans.
- Book artisans for services.
- Review artisans after completed services.
- Receive useful recommendations and search assistance.

The long-term goal is to evolve the project beyond the academic MVP into a production-ready platform.

---

## 🧭 Project Principles

Artisan Connect follows these core principles:

1. **MVP first** — Build the essential product before advanced features.
2. **Design for growth, don't build for growth** — Make sound architectural decisions without unnecessary complexity.
3. **One table answers one business question** — Keep database responsibilities clear.
4. **One source of truth** — Avoid duplicate sources of important data.
5. **Store facts, calculate values** — Persist factual data and calculate derived values when needed.
6. **Freeze approved modules** — Once a structure is approved and frozen, it should not be casually redesigned.
7. **Design dependencies before dependents** — Build foundational components before components that depend on them.
8. **Avoid overengineering** — Every component must have a clear purpose.
9. **Modular architecture** — Keep the system organized into maintainable modules.

---

## 🏗️ System Architecture

The backend follows a layered architecture:

```text
Frontend
   │
   │ HTTP / JSON
   ▼
Django REST API
   │
   ▼
Views / API Logic
   │
   ▼
Serializers & Validation
   │
   ▼
Business Logic
   │
   ▼
Django ORM
   │
   ▼
PostgreSQL
```

The frontend does **not** communicate directly with PostgreSQL.

Django is responsible for:

- API endpoints
- Authentication and authorization
- Request validation
- Business rules
- Database operations
- Serialization
- Communication with AI components
- Returning structured responses to the frontend

This separation also allows future clients, such as a Flutter application, to consume the same backend API.

---

## 🛠️ Technology Stack

### Backend

- Python
- Django
- Django REST Framework
- Django ORM
- PostgreSQL (via psycopg)
- SimpleJWT (token authentication, with token blacklisting)
- Brevo (transactional email over SMTP)

### Frontend

- HTML
- CSS
- Bootstrap
- JavaScript

### Maps & Location

- OpenStreetMap (map tiles, shown with Leaflet on the frontend)
- Nominatim (OpenStreetMap's address ↔ coordinates lookup)

### AI

- Natural Language Processing (NLP)
- Recommendation Engine
- Classification
- Regression
- Rule-based filtering

### Recent validation status

The project has been validated with real Django simulations covering the full marketplace flow:

- smart-search query matching for natural-language service requests
- current-location and saved-location coordinate resolution
- nearby-artisan discovery in map-style result sets
- booking lifecycle from `PENDING` to `FINALIZED`
- dispute handling and admin finalization

A dedicated regression test now verifies the map/nearby-artisan flow in `locations/tests.py`:

- `MapNearbyArtisanFlowTests`
- confirms current and saved location modes return the same nearby artisan markers
- confirms only verified artisans within range are included
- confirms far or pending artisans are excluded

---

## 📦 Project Modules

The system is organized around the following modules:

- **Authentication**
- **User Management**
- **Service Management**
- **Booking**
- **Reviews & Ratings**
- **Location**
- **Notifications**
- **Administration**
- **AI**

### Current Authentication Tables

- `accounts_user` — every account (customer, artisan, admin)
- `accounts_emailverificationtoken` — email verification links
- `accounts_passwordresettoken` — password reset codes
- `token_blacklist_outstandingtoken` / `token_blacklist_blacklistedtoken` — login sessions (JWT refresh tokens) and revoked ones; there is no separate sessions table

### Current User Management Tables

- `customers_customer`
- `artisans_artisan`

### Service Management Tables

- `services_service`
- `services_servicekeyword` — alternative words customers use for each service (Smart Search)
- `artisans_artisan_services` — which services each artisan offers

Service categories are postponed.

### Booking, Review & Location Tables

- `bookings_booking`
- `ai_searchlog` — Smart Search history (kept 12 months)
- `reviews_review`
- `locations_savedlocation`

Additional modules are introduced according to their dependencies and approved development stage.

---

## 👥 User Roles

The main user types are:

### Customer

Customers can:

- Create and manage an account.
- Search for services and artisans.
- Use location-based discovery.
- Book artisans.
- View booking history.
- Review artisans after completed bookings.
- Manage saved locations.
- Receive notifications.

### Artisan

Artisans can:

- Create and manage an artisan profile.
- Provide services.
- Receive and manage bookings according to system rules.
- Maintain service information.
- Build a reputation through completed jobs and customer reviews.

### Administrator

Administrators manage and monitor the platform through the administrative system.

Higher-level administrative capabilities, such as advanced moderation and custom administration dashboards, are planned for later versions where appropriate.

---

## ✉️ Email Verification

Every customer and artisan account has an email address, and email verification confirms the account owner actually controls it. It exists for two specific reasons only:

1. **Account recovery** — the password-reset code is sent to the account's email. Reset works even if the email was never verified, and completing a reset marks it verified (receiving the code proves the user controls the inbox).
2. **Preventing duplicate accounts against the same address** — `User.email` is already a unique column, so this isn't about allowing a second signup; it confirms the person signing up actually owns the address they claimed.

**It is intentionally non-blocking.** An unverified customer or artisan can still log in, book/receive bookings, and use the platform fully — verification status never gates any feature in Version 1. A verification email (with a 24-hour link) is sent automatically on registration, and can be resent on request.

Outgoing email is sent through **Brevo**, chosen over raw SMTP (e.g. a personal Gmail account) for reliable deliverability without needing to manage SPF/DKIM on a personal domain.

Email addresses are treated as **case-insensitive**: they are stored in lowercase, and registering `John@Gmail.com` when `john@gmail.com` already exists is rejected as a duplicate. Resending a verification email is limited to 3 requests per hour.

---

## 🔑 Password Reset

A customer or artisan who forgets their password recovers their account through a 6-digit code sent to their email:

```text
1. POST /api/v1/accounts/password-reset/request   { email }
        → a 6-digit code is emailed (valid 10 minutes)
2. POST /api/v1/accounts/password-reset/verify    { email, code }
        → returns a one-time reset_token (valid 15 minutes)
3. POST /api/v1/accounts/password-reset/confirm   { reset_token, new_password, confirm_password }
        → password changed; the user logs in with the new password
```

Rules:

- **Requesting a code never reveals whether an email is registered** — the response is identical either way, so the endpoint can't be used to find out who has an account.
- Each code allows **at most 5 wrong attempts**, after which it stops working (even the correct code). Requesting a new code cancels any previous one.
- Codes are stored hashed, never in plain text. The reset token can only be used once.
- The new password must pass the same strength rules as registration (both reject, among other things, a password too similar to the username).
- Completing a reset **logs out every device** (all existing sessions are revoked), in case the account was being used by someone else.
- Completing a reset also marks the email as verified (receiving the code proves the user controls the inbox), and a "your password was changed" notice is emailed.
- Requests are rate-limited: 5 code requests and 10 verification attempts per hour.

---

## 🔁 Service Change Requests

An artisan's services are not freely editable once set. Selecting services is a two-stage flow: an initial selection at registration, and a controlled **Service Change Request** for any change after that.

```text
Artisan
   ↓
Select 1–3 existing services
   ↓
Initial services
   ↓
[Later] Want to change services?
   ↓
Submit Service Change Request
   ↓
Give reason
   ↓
Admin reviews
   ↓
Approve / Reject
   ↓
If approved → services updated
   ↓
12-month waiting period
```

Key rules:

- An artisan selects 1–3 services at registration; this becomes their initial service list.
- Changing services afterward is never a direct profile edit — it must go through a **Service Change Request**.
- Every request must include a reason for the requested change.
- An admin reviews each request and either approves or rejects it.
- If approved, the artisan's services are updated and the artisan enters a **12-month waiting period** before another Service Change Request can be submitted.
- This prevents frequent switching that would undermine the artisan's price/service history and customer trust.

**Status:** documented business rule, not yet implemented in the backend (no `ServiceChangeRequest` model/table exists yet). See the Current Status table.

---

## 📍 Location-Based Discovery

Location is a core part of Artisan Connect.

The platform is designed to use:

- User live location
- Optional saved locations
- OpenStreetMap

Customers can use their location to discover relevant artisans nearby.

Saved locations are limited to **five per customer**.

### How Nearby Search Works

A customer searches from one of two starting points:

```text
GET /api/v1/locations/nearby-artisans
        │
        ├── current  →  ?location_type=current&latitude=..&longitude=..
        │                (live GPS supplied by the device; the default when
        │                 location_type is omitted)
        │
        └── saved    →  ?location_type=saved&location_id=5
                         (one of the customer's own saved locations)
```

- Only **verified** artisans who have set a location appear in results. Pending/rejected artisans, and verified artisans with no coordinates, are never returned.
- The search radius is **10 km** (straight-line distance, Haversine formula). Results are ordered nearest first and include `distance_km`.
- The backend is the source of truth for eligibility, distance, and ordering. The map only displays what the API returns.

### Map Markers

Each result is a map marker containing only what a customer needs to discover an artisan — e.g. **"John Plumbing · ✓ Verified · 3.42 km away"**:

| Field                              | Meaning                                                                                                                                                                        |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `id`                               | Used to open the artisan's profile / book them                                                                                                                                 |
| `name`                             | Business name (falls back to the artisan's full name)                                                                                                                          |
| `is_verified`                      | Always true in results — only verified artisans are shown                                                                                                                      |
| `distance_km`                      | Calculated on the server, measured to the same rounded position as the pin (so repeated searches from different points can't be used to work out the artisan's exact location) |
| `location`                         | The artisan's location in readable words (e.g. "Yaba, Lagos")                                                                                                                  |
| `latitude` / `longitude`           | Pin position, **rounded to ~110 m** so it never points at a specific building (an artisan's location may be their home)                                                        |
| `average_rating` / `review_count`  | From reviews of completed jobs                                                                                                                                                 |
| `starting_price` / `maximum_price` | Price range, derived from the artisan's services                                                                                                                               |

Phone numbers, emails, usernames, and exact coordinates are never included. The response also returns an `origin` (the point searched from) so the map can place the customer's 📍, including when searching from a saved location:

```text
Backend → nearby artisans → rounded coordinates + distance → API response
   → Frontend → OpenStreetMap:  📍 Customer   🔵 Artisan   🔵 Artisan   🔵 Artisan
```

- Artisans set their own location (`latitude`/`longitude`, plus a `default_location` description) through their profile. Only verified artisans can update it, and it has no cooldown.

### Address Lookup (OpenStreetMap)

The backend uses OpenStreetMap's **Nominatim** service to convert between addresses and coordinates, so users don't have to know their latitude/longitude:

- `GET /api/v1/locations/geocode?q=<address>` — typed address → up to five matching places with coordinates. The user picks and confirms the right one before saving a location or booking a job there.
- `GET /api/v1/locations/reverse-geocode?latitude=..&longitude=..` — live GPS → the nearest readable address (e.g. to show "You are near …").

Nominatim is a free public service with a strict usage policy, which the backend enforces in one place: at most **one request per second** to OpenStreetMap, an identifying User-Agent, results **cached for 24 hours**, and a per-user limit of 20 lookups per minute (no search-as-you-type). Results in both directions are restricted to Nigeria by default. If OpenStreetMap is unreachable the endpoints return **503**, and nothing else in the app is affected.

OpenStreetMap on the frontend is for **visualization and navigation**: showing the markers above (Leaflet with OpenStreetMap tiles), and giving the **artisan directions to the job address during an accepted job**. Customers see artisans' distances from their location rather than navigating to them.

### Saved Location Rules

- A customer can create, list, view, and delete their own saved locations (maximum five).
- Saved locations are private to their owner. Requesting another customer's saved location — directly, or as `location_id` in a nearby search — returns **404 Not Found**, exactly like a location that doesn't exist, so saved locations can't be discovered by guessing IDs.
- Nearby search is only available to customers, and is limited to 30 searches per minute per user. It can be limited to one service with `?service=<id>` (used by Smart Search).

### Job Location Privacy

A booking stores the customer's job address and GPS coordinates so the artisan can travel to the job. To stop customers and artisans taking work outside the platform, that location is only revealed while it's actually needed:

| Booking status        | Customer | Artisan                         | Admin  |
| --------------------- | -------- | ------------------------------- | ------ |
| Pending               | ✅       | ❌ (decides from distance/area) | ✅     |
| Accepted              | ✅       | ✅                              | ✅     |
| In progress           | ✅       | ✅                              | ✅     |
| Completed             | ✅       | ❌                              | ✅     |
| Disputed              | ✅       | ❌                              | ✅     |
| Cancelled / Finalized | erased   | erased                          | erased |

- When a booking is **finalized, cancelled, or rejected**, the job address and coordinates are permanently erased from the database. The rest of the job history (service, dates, status, review) is kept for both parties.
- Reviews are visible to all users, so they only ever include a booking summary (service and dates) — never the job location, and never the booking status (so whether a job was disputed stays between the two parties and admins).

---

## 📅 Booking & Reviews

Bookings form the connection between customers, artisans, and services.

A simplified relationship is:

```text
Customer
   │
   ▼
Booking
   │
   ├── Artisan
   │
   └── Service
```

Reviews are tied to completed work rather than being freely submitted against any artisan.

### Booking Lifecycle

```text
PENDING ──artisan accepts──▶ ACCEPTED ──artisan starts──▶ IN_PROGRESS
   │                            │                              │
   ├─artisan rejects─┐          │                    artisan marks complete
   └─customer cancels┴──────────┴─▶ CANCELLED                  ▼
                                                           COMPLETED
                                                               │
                                   customer confirms ──────────┼──▶ FINALIZED
                                   no reply within 3 days ─────┤
                                                               │
                         customer disagrees (with a reason) ───┴──▶ DISPUTED
                                                                       │
                                        admin finalizes ───────────────┼──▶ FINALIZED
                                        admin reopens  ────────────────┴──▶ IN_PROGRESS
                                                                  (artisan fixes the work and
                                                                   marks it complete again)
```

- A customer can cancel a booking while it is **pending or accepted**, but not once work has started.
- **Both parties must agree a job is finished.** The artisan marking the job complete counts as their confirmation; the customer is then asked to confirm on their side. This protects artisans from customers who forget to confirm, and gives the app a record that both sides agreed.
- A customer who hasn't confirmed receives **email reminders** 24 hours, 48 hours, and 66 hours after completion (the last one is marked as the final reminder). If they still haven't confirmed **3 days** after completion, the booking is finalized automatically.
- **The customer can disagree** that the job is done if they aren't satisfied, but must give a reason of **at least 20 characters**. The booking becomes **DISPUTED**: reminders and auto-finalization stop, and an admin decides. The reason is visible to the customer, the artisan, and admins only — never in public reviews.
- **Every active admin is emailed when a dispute is opened**, with the booking number, service, both parties' names, the customer's reason, and how to settle it. (This will move to in-app notifications when the Notifications module is built.) A failed email never blocks the dispute.
- An admin settles a dispute by either **finalizing** the booking or **reopening** it, which sends the job back to the artisan (IN_PROGRESS, job address visible again, dispute reason kept so they know what to fix). When the artisan marks it complete again, the customer gets a fresh confirm/disagree choice, fresh reminders, and a fresh 3-day window.
- Only an admin can finalize a booking manually. Nobody else can.
- Finalizing (by any route) erases the job location. Each booking records how it was finalized: confirmed by the customer, automatically, or by an admin.
- Reminders and auto-finalization are run by `python manage.py process_completed_bookings`, which should be scheduled to run every hour (Windows Task Scheduler or cron).

### Review Rules

- A customer must have completed a booking before reviewing an artisan. A review can be left once the artisan marks the job complete, and is still allowed while the booking is disputed or after it is finalized, so finalizing can never be used to prevent a review and an unhappy customer can always say so.
- Reviews are associated with the relevant booking.
- An artisan cannot review themselves.
- A review can be edited **exactly once**, only by the customer who wrote it, and only within **24 hours** of posting it. Editing only the rating keeps the existing comment.
- The reviewer is always the logged-in customer. A review can't be created or edited on behalf of another customer, and the artisan is always taken from the booking.

---

## 🧩 Rules Established During Implementation

The following rules were not part of the original SRS/design but were established while building the backend. They are now treated as approved, in effect the same as anything else in this document:

- **Artisan profile fields have independent 6-month cooldowns.** `full_name`, `profile_picture`, and `business_name` can each be changed at most once every 6 months, tracked independently per field. `phone_number` and `default_location` have no cooldown.
- **A booking must include the job address and GPS location** — the artisan can't travel to the job without them. GPS coordinates with extra decimal places (common from phones) are rounded rather than rejected.
- **Inactive services don't count toward an artisan's price range.** An artisan keeps a deactivated service on their profile, but it can't be booked and no longer affects their starting/maximum price. Admins can still list inactive services.
- **Customers can edit their own profile at any time** (`PATCH /api/v1/customers/customer/details`): username, full name, profile picture, and default location, with no cooldowns. Their **phone number and email can never be changed** through the app; a request that tries to is rejected rather than silently ignored. Usernames must be unique (ignoring capitalisation).
- **Usernames are private.** Other users never see someone's username (it is half of their login details); they see the full name or business name instead.
- **Logging in and registering are rate-limited** (10 login attempts per minute and 10 registrations per hour from one address) to slow down password guessing and protect the email quota.
- **Admin accounts are created with `python manage.py createsuperuser`**, which gives them the admin role. Customers and artisans should always be created through registration, which also creates their profile.
- **A service's price change updates every artisan who offers it**, including when edited in Django admin. In Django admin, an artisan's price range and verification status are read-only; artisans are approved or rejected with the "Approve/Reject selected pending artisans" actions, which follow the same pending-only rule as the API.
- **Re-submitting an unchanged profile value doesn't count as a change**, so it never starts or trips a 6-month cooldown.
- **Pending and rejected artisans cannot log in.** An artisan can only log in once an admin has approved them.
- **Only verified artisans can edit their profile.** An artisan with `PENDING` or `REJECTED` verification status cannot update any profile field until an admin approves them.
- **An artisan's price range is a calculated value, never a direct input.** `starting_price` and `maximum_price` are derived automatically as the min/max across the artisan's currently assigned services, recalculated whenever the service list changes. This follows the "store facts, calculate values" principle above.
- **Services enforce `minimum_price ≤ maximum_price`.** Both at the model level and in the API serializer.
- **Artisan verification is a two-outcome review, not a multi-step pipeline.** An admin reviews a `PENDING` artisan and either approves or rejects them; only pending artisans can be acted on (an already verified/rejected artisan cannot be re-decided through this endpoint).
- **Phone numbers are never exposed between a customer and an artisan, in either direction.** This was already an approved decision (see "Phone numbers remain private" below) but wasn't actually enforced everywhere it needed to be — the artisan/customer detail nested inside a booking or review, and the public artisan marketplace listing, were all leaking `phone_number` before this was corrected. Customers and artisans are only meant to reach each other through the application itself.
- **No contact details cross between a customer and an artisan — not just phone numbers.** Email addresses and the customer's default location are also hidden from the other party, and the job location follows the visibility rules in [Job Location Privacy](#job-location-privacy). The purpose is to keep jobs, payments, and reviews on the platform.
- **Job locations are erased when a booking is cancelled or rejected**, not only when it is finalized, so an abandoned booking doesn't keep a customer's address indefinitely.
- **Nearby search can start from a saved location**, not only live GPS, and the saved location must belong to the searching customer.
- **A review is always written by the logged-in customer.** The create and edit endpoints previously accepted the customer's id from the request body, which would have allowed one customer to review or edit in another customer's name; the reviewer is now always taken from the login session.
- **Email addresses are unique regardless of capitalisation**, so the same inbox can't be used to create two accounts.
- **Password reset uses a 6-digit emailed code**, with attempt limits and a single-use reset token (see [Password Reset](#-password-reset)).
- **Viewing a booking is restricted to its own customer, its own artisan, or an admin.** Listing and fetching-by-id were previously open to any authenticated user; this has been corrected to match the "view only your own data" principle already applied elsewhere (saved locations, artisan profile).

---

## 🤖 AI Roadmap

### Smart Search

Smart Search lets a customer describe what they need in their own words — a trade (`plumber`) or a problem (`my bathroom is leaking`) — and finds the matching service and nearby artisans in one step.

```text
Query ("my bathroom is leaking")
 ↓
Smart Search            → identifies the service
 ↓
Service = Plumbing
 ↓  ── the system takes over ──
Customer location       → current GPS or a saved location
 ↓
10 km radius
 ↓
Verified artisans offering that service
 ↓
Recommendation ranking  → V1: closest first (the recommendation engine will replace this step)
```

`GET /api/v1/ai/search?q=<text>&location_type=current&latitude=..&longitude=..` (or `location_type=saved&location_id=<id>`). Customers only; the text must be 2–200 characters; limited to 30 searches per minute.

**What counts as a search query:** free text describing either the service or the problem.

**How matching works (V1, rule-based):**

1. The text is normalized: lowercase, punctuation and extra spaces removed.
2. **Exact service name** — `painting`, `Painting!` → Painting.
3. **Keywords and synonyms** — each service has its own list of alternative words, stored in a separate `ServiceKeyword` table (the `Service` table itself is unchanged):

   ```text
   Service
     └── Plumbing
           └── ServiceKeyword: pipe, leaking pipe, tap, faucet, sink, water leak, bathroom, ...
   ```

   Word forms are treated as the same word (`leaking`/`leaks` → `leak`, `plumber`/`plumbing`), and multi-word keywords (`leaking pipe`) count for more than single words.

4. **Typo tolerance** — `electrecian` → Electrical, `plumbng` → Plumbing.
5. **Scoring** — every matching keyword adds to that service's score, and the clearest winner is chosen.

**When the system is uncertain:**

| Result                   | When                                                                            | What the customer gets                                                                         |
| ------------------------ | ------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Confident                | One service clearly wins                                                        | The service and nearby artisans offering it, as map markers                                    |
| Confident, nobody nearby | One service wins but no verified artisan offering it is within 10 km            | "No Plumbing artisans found within your area." with empty results                              |
| Unsure                   | Two or more services are close (e.g. `roof is leaking` → Carpentry or Plumbing) | "Did you mean…?" with up to 3 services to choose from                                          |
| No match                 | Nothing matches, or the text is too vague (`I need help with something`)        | "We couldn't identify what you need. Please clarify…" plus the list of services to choose from |

Only **active** services are ever matched. Keywords are managed by admins on each service's page in Django admin; the V1 starter set is English.

**Search log:** every search is recorded (customer, text, matched service, confidence) so admins can find words customers use that aren't keywords yet (filter on "No match"/"Unsure"), and as training data for V2. Search logs are deleted automatically after **12 months** by `python manage.py purge_search_logs` (schedule it daily).

**V1 vs V2:**

- **V1 (built):** rule-based matching (exact name, keywords/synonyms, word forms, typo tolerance, scoring), three confidence levels, combined service + nearby search, English keywords, search log, keyword management in admin.
- **V2 (planned):** a trained machine-learning classifier built from the search log; more languages (Pidgin, Yoruba, Igbo, Hausa); personalisation from search history; the recommendation engine replacing distance-only ranking; queries needing more than one service (e.g. "paint and fix the wiring").

### Recommendation Engine

Ranks suitable nearby artisans using factors such as:

- Relevance
- Location
- Rating
- Completed jobs
- Response characteristics
- Verification status

### Scam Detection

Planned to combine NLP and anomaly-detection techniques to identify potentially suspicious activity.

### Labour Price Estimation

Regression can be used to estimate labour charges.

**Important:** labour estimation concerns labour costs only; material costs are excluded.

---

## 🚀 Version Roadmap

### Version 1 — MVP

The first release focuses on the core platform:

- Django backend
- PostgreSQL
- Bootstrap frontend
- OpenStreetMap
- Authentication
- Customer and artisan management
- Service management
- Booking
- Reviews
- Notifications
- AI assistant
- Smart search
- Labour price estimation
- Email verification
- Django Admin

### Version 2

Planned enhancements include:

- Verification levels
- Community suggestions
- Date of birth support
- Enhanced AI/recommendations
- Custom admin dashboard
- Additional analytics

### Version 3

Long-term features include:

- Flutter mobile application
- Voice assistant
- Video calling
- Emergency requests

---

## 🔐 Important Architecture Decisions

The following decisions are part of the project's approved architecture:

- Django replaced Flask as the backend framework.
- PostgreSQL is the approved database.
- Bootstrap is the Version 1 frontend framework.
- OpenStreetMap is the approved map provider.
- Email verification is included in Version 1.
- Multiple active device sessions are supported.
- Usernames are editable by customers (artisans keep the username they registered with).
- Phone numbers remain private.
- **One email, one account, one role — permanently.** An email address (case-insensitive) can belong to only one account, whether customer, artisan, or admin. An artisan who wants to hire another artisan must register a separate customer account with a different email. This applies to all future versions.
- Customer suggestions for new service categories are postponed.
- Date of birth is postponed to a later version.
- Labour price estimation excludes material costs.
- Artisan profile fields (`full_name`, `profile_picture`, `business_name`) each have an independent 6-month change cooldown.
- An artisan's price range is always calculated from assigned services, never set directly.
- Changing an artisan's services after registration requires an approved Service Change Request with a 12-month cooldown (see [Service Change Requests](#-service-change-requests)).

---

## 🧊 Frozen Tables & Change Control

Artisan Connect uses a **Frozen Tables** approach.

Before a table is frozen, it must be reviewed for:

1. Purpose
2. Normalization
3. Security
4. Scalability
5. Simplicity

After approval, the table becomes part of the project's stable design.

A new requirement should not automatically result in changing a frozen table. The existing Project Bible and Decision Rules must be checked first.

---

## 📖 Project Bible

The **Project Bible** is the master source of truth for Artisan Connect.

It records:

- Approved architecture decisions
- Database decisions
- Development principles
- Version boundaries
- Roadmap
- Modules
- Business and engineering rules
- Future plans

Any major change to the system should be evaluated against the Project Bible before implementation.

---

## 🗺️ Development Phases

The project follows these major phases:

```text
Phase 0 → Product Vision
Phase 1 → SRS
Phase 2 → Architecture & Database Design
Phase 3 → Django Setup
Phase 4 → Backend Development
Phase 5 → Frontend Development
Phase 6 → Testing
Phase 7 → Deployment
```

### Current Development Direction

The project has progressed from planning and system design into **Django backend development**.

The backend work includes:

- Django project setup
- Application/module structure
- PostgreSQL integration
- Models
- Migrations
- Serializers
- URLs
- Views/API endpoints
- Business logic
- Validation
- Testing

---

## 🧪 Development Philosophy

Development follows a controlled process:

```text
Approved Design
      ↓
Implementation
      ↓
Validation
      ↓
Testing
      ↓
Approval
      ↓
Next Module
```

We do not redesign approved components simply because another implementation appears easier.

When a conflict appears, the existing Project Bible, Decision Rules, and frozen structures are checked first.

---

## 👨‍💻 Team Roles

### Product Owner & Lead Developer

Responsible for:

- Product vision
- Feature decisions
- Product direction
- Application development
- Final product decisions

### Technical Architect & AI Consultant

Responsible for:

- System architecture
- Database design
- Backend structure
- AI integration
- Code review
- Security considerations
- Performance recommendations
- Maintaining alignment with the Project Bible

---

## 📁 Repository Structure

The Django project is organized into independent applications/modules so that each part of the system has a clear responsibility.

A typical structure will follow the pattern:

```text
artisan_connect/
│
├── config/
├── accounts/
├── customers/
├── artisans/
├── services/
├── bookings/
├── reviews/
├── locations/
├── notifications/     (planned)
├── administration/    (planned)
├── ai/                (Smart Search; recommendations and price estimation planned)
│
├── manage.py
├── requirements.txt
└── README.md
```

The exact structure may evolve as implementation progresses, but changes must remain consistent with the approved architecture.

---

## 📌 Current Status

**Project Status: Active Development**

| Area                                     | Status                |
| ---------------------------------------- | --------------------- |
| Product Vision                           | ✅ Complete           |
| Project Bible                            | ✅ Established        |
| SRS / Requirements                       | ✅ Established        |
| Architecture                             | ✅ Established        |
| Database Design                          | ✅ Established        |
| Django Setup                             | ✅ Complete           |
| PostgreSQL Integration                   | ✅ Complete           |
| Authentication Foundation                | ✅ Complete           |
| Email Verification                       | ✅ Complete           |
| Password Reset                           | ✅ Complete           |
| Customer Module                          | ✅ Complete           |
| Service Management                       | 🔄 In Progress        |
| Service Change Requests                  | ⏳ Planned            |
| Booking                                  | ✅ Complete (backend) |
| Reviews & Ratings                        | ✅ Complete (backend) |
| Location                                 | 🔄 In Progress        |
| Notifications                            | ⏳ Planned            |
| Smart Search (V1)                        | ✅ Complete (backend) |
| AI Features (recommendations, V2 search) | ⏳ Planned/Developing |
| Frontend                                 | ⏳ Upcoming           |
| Testing                                  | 🔄 Ongoing            |
| Deployment                               | ⏳ Later Phase        |

---

## 📜 Change Policy

Before making a major change:

1. Check the Project Bible.
2. Check the relevant Decision Rules.
3. Check whether the affected table/module is frozen.
4. Confirm that the change belongs to the current version.
5. Consider its effect on existing relationships and business logic.
6. Only then implement the change.

**The goal is to build Artisan Connect deliberately, not simply quickly.**

---

## 📄 License

This project is currently being developed as an academic/final-year project. Licensing and commercial-use terms can be defined when the project moves toward public or commercial release.
