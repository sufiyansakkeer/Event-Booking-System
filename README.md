# Event Booking System

A production-ready Event Booking System built with **FastAPI**, **PostgreSQL**, **Redis**, **Celery**, and **SQLAlchemy 2.0**.

This project focuses on handling **concurrency**, **booking workflows**, **idempotency**, and **background processing** in a scalable backend architecture.

---

# Features

- User authentication with JWT
- Create and manage events
- Seat reservation with overbooking prevention
- Booking workflow:
  - Reserve
  - Confirm
  - Cancel
- Redis caching for event listings
- Celery background jobs for email notifications
- Idempotency key handling for payment simulation
- Optimistic locking using SQLAlchemy versioning
- Load testing with Locust
- Dockerized setup
- Clean Architecture implementation
- Async-first backend using FastAPI + SQLAlchemy

---

# Tech Stack

| Category | Technology |
|---|---|
| Backend Framework | FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy 2.0 (Async) |
| Cache | Redis |
| Background Tasks | Celery |
| State Machine | transitions |
| Authentication | JWT (python-jose) |
| Migration Tool | Alembic |
| Validation | Pydantic v2 |
| Load Testing | Locust |
| Containerization | Docker & Docker Compose |

---

# Project Structure

```text
app/
├── api/                # Routes / Controllers
├── core/               # Config, security, utilities
├── database/           # DB session & base
├── models/             # SQLAlchemy models
├── repositories/       # Data access layer
├── services/           # Business logic
├── schemas/            # Pydantic DTOs
├── workers/            # Celery tasks
├── cache/              # Redis caching
├── state_machine/      # Booking workflow
├── tests/              # Unit & integration tests
└── main.py
```

---

# Booking Workflow

```text
RESERVED → CONFIRMED → CANCELLED
```

Business rules enforced:

- Cannot book past events
- Maximum 5 active bookings per user
- Cancellation only before allowed deadline
- Prevent double booking/payment using idempotency keys

---

# Optimistic Concurrency Handling

This project prevents overbooking using SQLAlchemy optimistic locking.

Example:

```python
version_id = Column(Integer, nullable=False)

__mapper_args__ = {
    "version_id_col": version_id
}
```

If multiple users try booking simultaneously, stale updates are rejected safely.

---

# Redis Usage

Redis is used for:

## 1. Caching Event Listings

Frequently accessed event data is cached to reduce database load.

```text
Client → Redis Cache → PostgreSQL
```

## 2. Idempotency Keys

Prevents duplicate payment processing:

```text
Request → Check Redis Key → Process Once → Store Result
```

## 3. Celery Broker

Redis acts as the message broker between FastAPI and Celery workers.

---

# Celery Background Tasks

Used for:

- Email confirmations
- Retry handling
- Async notification processing

Example task:

```python
@celery.task
def send_booking_email(email: str):
    print(f"Sending confirmation email to {email}")
```

---

# API Features

## Auth

- Register
- Login
- JWT Authentication

## Events

- Create event
- Update event
- List events
- Event details

## Bookings

- Reserve seat
- Confirm booking
- Cancel booking
- View booking history

---

# Installation

## Clone Repository

```bash
git clone <your-repo-url>
cd event-booking-system
```

---

# Environment Variables

Create a `.env` file:

```env
DATABASE_URL=postgresql+asyncpg://postgres:password@db:5432/event_booking
REDIS_URL=redis://redis:6379
SECRET_KEY=your_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

---

# Run with Docker

```bash
docker-compose up --build
```

Application:

```text
http://localhost:8000
```

Swagger Docs:

```text
http://localhost:8000/docs
```

---

# Database Migrations

## Create Migration

```bash
alembic revision --autogenerate -m "initial migration"
```

## Apply Migration

```bash
alembic upgrade head
```

---

# Run Celery Worker

```bash
celery -A app.workers.celery_worker worker --loglevel=info
```

---

# Run Tests

```bash
pytest
```

---

# Load Testing

Run Locust:

```bash
locust
```

Then open:

```text
http://localhost:8089
```

Simulate concurrent booking requests to test race condition handling.

---

# Key Concepts Implemented

- Async FastAPI architecture
- Repository pattern
- Service layer pattern
- Dependency Injection with `Depends`
- Optimistic concurrency control
- Distributed caching
- Background job processing
- Idempotency handling
- State machine workflow
- Dockerized deployment

---

# Future Improvements

- Payment gateway integration
- WebSocket live seat updates
- Event analytics dashboard
- Role-based admin panel
- Kubernetes deployment
- CI/CD pipeline
- OpenTelemetry tracing
- Rate limiting

---

# Learning Outcomes

This project helped in understanding:

- Real-world concurrency problems
- Redis caching patterns
- Celery async workflows
- Production backend architecture
- Database transaction handling
- Scalable FastAPI application design

---

# Author

**Sufiyan Sakkeer**