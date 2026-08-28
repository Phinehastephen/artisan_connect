[README(1).md](https://github.com/user-attachments/files/31547767/README.1.md)
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
- PostgreSQL

### Frontend

- HTML
- CSS
- Bootstrap
- JavaScript

### Maps & Location

- OpenStreetMap

### AI

- Natural Language Processing (NLP)
- Recommendation Engine
- Classification
- Regression
- Rule-based filtering

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

- `users`
- `user_sessions`
- `password_reset_tokens`

### Current User Management Tables

- `customers`

### Service Management Tables

- `service_categories`
- `services`
- `artisan_services`

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

## 📍 Location-Based Discovery

Location is a core part of Artisan Connect.

The platform is designed to use:

- User live location
- Optional saved locations
- OpenStreetMap

Customers can use their location to discover relevant artisans nearby.

Saved locations are limited to **five per customer**.

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

### Review Rules

- A customer must have completed a booking before reviewing an artisan.
- Reviews are associated with the relevant booking.
- An artisan cannot review themselves.
- Review editing is restricted according to the approved project rules.

---

## 🤖 AI Roadmap

### Smart Search

Uses NLP to understand what a customer is looking for and identify relevant services/artisans.

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
- Usernames are editable according to the approved account rules.
- Phone numbers remain private.
- Customer suggestions for new service categories are postponed.
- Date of birth is postponed to a later version.
- Labour price estimation excludes material costs.

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
artisan-connect/
│
├── config/
├── accounts/
├── customers/
├── artisans/
├── services/
├── bookings/
├── reviews/
├── locations/
├── notifications/
├── administration/
├── ai/
│
├── manage.py
├── requirements.txt
└── README.md
```

The exact structure may evolve as implementation progresses, but changes must remain consistent with the approved architecture.

---

## 📌 Current Status

**Project Status: Active Development**

| Area | Status |
|---|---|
| Product Vision | ✅ Complete |
| Project Bible | ✅ Established |
| SRS / Requirements | ✅ Established |
| Architecture | ✅ Established |
| Database Design | ✅ Established |
| Django Setup | ✅ Complete |
| PostgreSQL Integration | ✅ Complete |
| Authentication Foundation | ✅ Complete |
| Customer Module | ✅ Complete |
| Service Management | 🔄 In Progress |
| Booking | 🔄 Development |
| Reviews & Ratings | 🔄 Development |
| Location | ⏳ Planned |
| Notifications | ⏳ Planned |
| AI Features | ⏳ Planned/Developing |
| Frontend | ⏳ Upcoming |
| Testing | 🔄 Ongoing |
| Deployment | ⏳ Later Phase |

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
