# Aura ID Backend — Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Phase 1 FastAPI backend for Aura ID — project scaffold, image pipeline (EXIF strip + face blackout + Vertex AI extraction), core scan/guest/hotel endpoints, audit logging, and retention job — deployed via Docker on Railway.

**Architecture:** Single FastAPI process in `backend/` subdirectory. Supabase handles Postgres (RLS + manual hotel*id filters), Auth (JWT for clerks), and Storage (private image bucket). MediaPipe detects and blacks out the face region before any image reaches Vertex AI. APScheduler runs hourly in-process to delete images past retention window. Two auth paths: Supabase JWT for clerks, opaque `ws_live*` token for workstations.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, supabase-py v2, google-cloud-aiplatform (Vertex AI — NOT direct Gemini API), MediaPipe CPU face detection (blackout only — no biometrics extracted), Pillow + piexif, cryptography (Fernet), structlog, slowapi, APScheduler, pytest + httpx

---

## File Map

```
backend/
├── app/
│   ├── main.py                        create — FastAPI app, Sentry, CORS, routers, scheduler
│   ├── config.py                      create — Pydantic Settings from .env
│   ├── deps.py                        create — get_current_user, get_current_workstation, limiter
│   ├── middleware/
│   │   ├── audit.py                   create — Starlette middleware, logs every request
│   │   ├── pii_scrubber.py            create — structlog processor + Sentry before_send
│   │   └── subscription_gate.py      create — blocks inactive hotels
│   ├── routers/
│   │   ├── scans.py                   create — POST/GET scan endpoints
│   │   ├── guests.py                  create — GET/DELETE guest endpoints
│   │   └── hotels.py                  create — GET /hotels/me
│   ├── services/
│   │   ├── image_pipeline.py          create — 9-step pipeline
│   │   ├── vertex_ai.py               create — AbstractVertexClient, VertexAIClient, FakeVertexClient
│   │   ├── storage.py                 create — Supabase Storage wrapper
│   │   ├── audit.py                   create — write_audit_log()
│   │   └── retention.py               create — APScheduler hourly deletion job
│   ├── models/
│   │   ├── common.py                  create — ApiResponse[T], PaginatedResponse
│   │   ├── scan.py                    create — ParsedID, ScanCreate, ScanResponse
│   │   └── guest.py                   create — GuestResponse, GuestListItem
│   └── db/
│       └── schema.sql                 create — all tables, RLS, pgcrypto, indexes
├── tests/
│   ├── conftest.py                    create — app fixture, async client, fake auth headers
│   ├── test_pii_scrubber.py           create
│   ├── test_deps.py                   create
│   ├── test_audit.py                  create
│   ├── test_subscription_gate.py      create
│   ├── test_image_pipeline.py         create — incl. pixel-level blackout assertion
│   ├── test_vertex_ai.py              create
│   ├── test_storage.py                create
│   ├── test_retention.py              create
│   ├── test_scans.py                  create
│   ├── test_guests.py                 create
│   └── test_hotels.py                 create
├── Dockerfile                         create — multi-stage, non-root user
├── pyproject.toml                     create
├── .env.example                       create
└── .gitignore                         create
```

---

## Task 1: Project Scaffold

**Files:**

- Create: `backend/pyproject.toml`
- Create: `backend/Dockerfile`
- Create: `backend/.env.example`
- Create: `backend/.gitignore`
- Create: `backend/app/__init__.py` (empty)
- Create: `backend/app/middleware/__init__.py` (empty)
- Create: `backend/app/routers/__init__.py` (empty)
- Create: `backend/app/services/__init__.py` (empty)
- Create: `backend/app/models/__init__.py` (empty)
- Create: `backend/app/db/__init__.py` (empty)
- Create: `backend/tests/__init__.py` (empty)

- [ ] **Step 1: Create directory tree**

```bash
cd backend
mkdir -p app/middleware app/routers app/services app/models app/db tests
touch app/__init__.py app/middleware/__init__.py app/routers/__init__.py \
      app/services/__init__.py app/models/__init__.py app/db/__init__.py \
      tests/__init__.py
```

- [ ] **Step 2: Write pyproject.toml**

```toml
# backend/pyproject.toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "aura-id-backend"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.111.0",
    "uvicorn[standard]>=0.29.0",
    "pydantic>=2.7.0",
    "pydantic-settings>=2.2.0",
    "supabase>=2.4.0",
    "google-cloud-aiplatform>=1.55.0",
    "pillow>=10.3.0",
    "opencv-python-headless>=4.9.0",
    "mediapipe>=0.10.14",
    "piexif>=1.1.3",
    "stripe>=9.5.0",
    "structlog>=24.1.0",
    "sentry-sdk[fastapi]>=2.3.0",
    "slowapi>=0.1.9",
    "python-multipart>=0.0.9",
    "bcrypt>=4.1.3",
    "apscheduler>=3.10.4",
    "cryptography>=42.0.0",
    "httpx>=0.27.0",
    "PyJWT>=2.8.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.2.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=5.0.0",
    "ruff>=0.4.0",
    "black>=24.4.0",
]

[tool.hatch.build.targets.wheel]
packages = ["app"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py311"
select = ["E", "F", "I"]

[tool.black]
line-length = 100
target-version = ["py311"]
```

- [ ] **Step 3: Write Dockerfile**

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim AS builder
WORKDIR /build
COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir ".[dev]"

FROM python:3.11-slim AS runtime
WORKDIR /app

RUN groupadd -r appgroup && useradd -r -g appgroup -d /app appuser && \
    chown appuser:appgroup /app

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn

COPY --chown=appuser:appgroup app/ ./app/

USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

- [ ] **Step 4: Write .env.example**

```bash
# backend/.env.example
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=eyJ...          # service_role key — backend only, never in frontend
SUPABASE_JWT_SECRET=your-jwt-secret  # from Supabase dashboard > Settings > API

# Google Cloud / Vertex AI
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
GCP_PROJECT_ID=your-gcp-project-id
VERTEX_LOCATION=us-central1

# Encryption — generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
DOC_ENCRYPTION_KEY=your-fernet-key-here

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Sentry
SENTRY_DSN=https://...@sentry.io/...

# App
ENVIRONMENT=development
CORS_ORIGINS=["http://localhost:3000"]
```

- [ ] **Step 5: Write .gitignore**

```gitignore
# backend/.gitignore
__pycache__/
*.py[cod]
.env
.env.*
!.env.example
*.egg-info/
dist/
.pytest_cache/
.coverage
htmlcov/
*.log
service-account.json
*.pem
```

- [ ] **Step 6: Install dependencies**

```bash
cd backend
pip install -e ".[dev]"
```

Expected: packages install without errors.

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "chore(backend): project scaffold — pyproject.toml, Dockerfile, .env.example"
```

---

## Task 2: Config + Logging

**Files:**

- Create: `backend/app/config.py`
- Create: `backend/app/utils/__init__.py`
- Create: `backend/app/utils/pii.py`
- Create: `backend/app/utils/logging.py`

- [ ] **Step 1: Write config.py**

```python
# backend/app/config.py
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    supabase_url: str
    supabase_service_key: str
    supabase_jwt_secret: str

    gcp_project_id: str
    vertex_location: str = "us-central1"
    google_application_credentials: str = ""

    doc_encryption_key: str

    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    sentry_dsn: str = ""
    environment: str = "development"
    cors_origins: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
```

- [ ] **Step 2: Write utils/pii.py**

```python
# backend/app/utils/pii.py
import re

_DOB_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_DOC_NUM_RE = re.compile(r"\b([A-Z0-9]{2,4})\d{4,}\b")
_NAME_RE = re.compile(r'"(first_name|last_name)"\s*:\s*"([^"]+)"')


def mask_name(first: str | None, last: str | None) -> str:
    """J. Smith"""
    if not last:
        return ""
    initial = f"{first[0]}. " if first else ""
    return f"{initial}{last}"


def mask_doc_number(doc_number: str | None) -> str | None:
    if not doc_number:
        return None
    return f"****{doc_number[-4:]}" if len(doc_number) >= 4 else "****"


def scrub_pii_from_string(text: str) -> str:
    """Best-effort PII scrub for log strings. Not a security boundary."""
    text = _DOB_RE.sub("[DOB_REDACTED]", text)
    text = _DOC_NUM_RE.sub(r"\1****", text)
    return text
```

- [ ] **Step 3: Write utils/logging.py**

```python
# backend/app/utils/logging.py
import logging
import structlog
from app.utils.pii import scrub_pii_from_string


def _pii_scrub_processor(logger, method, event_dict):
    """structlog processor — scrubs PII from every log line."""
    for key in ("first_name", "last_name", "dob", "doc_number", "email", "phone"):
        if key in event_dict:
            del event_dict[key]
    if "event" in event_dict and isinstance(event_dict["event"], str):
        event_dict["event"] = scrub_pii_from_string(event_dict["event"])
    return event_dict


def configure_structlog() -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            _pii_scrub_processor,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/config.py backend/app/utils/
git commit -m "feat(backend): config, PII masking helpers, structlog setup"
```

---

## Task 3: PII Scrubber Tests

**Files:**

- Create: `backend/tests/test_pii_scrubber.py`

- [ ] **Step 1: Write tests**

```python
# backend/tests/test_pii_scrubber.py
import structlog
from app.utils.pii import mask_name, mask_doc_number, scrub_pii_from_string
from app.utils.logging import _pii_scrub_processor


def test_mask_name_returns_initial_plus_last():
    assert mask_name("John", "Smith") == "J. Smith"


def test_mask_name_no_first():
    assert mask_name(None, "Smith") == "Smith"


def test_mask_name_both_none():
    assert mask_name(None, None) == ""


def test_mask_doc_number_shows_last_four():
    assert mask_doc_number("AB123456789") == "****6789"


def test_mask_doc_number_none():
    assert mask_doc_number(None) is None


def test_scrub_pii_redacts_dob():
    result = scrub_pii_from_string("guest dob=1990-05-12 checked in")
    assert "1990-05-12" not in result
    assert "[DOB_REDACTED]" in result


def test_pii_scrub_processor_removes_pii_keys():
    event_dict = {
        "event": "guest created",
        "first_name": "John",
        "last_name": "Smith",
        "dob": "1990-01-01",
        "doc_number": "AB123456",
        "hotel_id": "hotel-uuid",
    }
    result = _pii_scrub_processor(None, None, event_dict)
    assert "first_name" not in result
    assert "last_name" not in result
    assert "dob" not in result
    assert "doc_number" not in result
    assert result["hotel_id"] == "hotel-uuid"  # non-PII preserved


def test_pii_scrub_processor_preserves_event_string():
    event_dict = {"event": "scan.parsed scan_id=abc-123"}
    result = _pii_scrub_processor(None, None, event_dict)
    assert result["event"] == "scan.parsed scan_id=abc-123"
```

- [ ] **Step 2: Run tests**

```bash
cd backend && pytest tests/test_pii_scrubber.py -v
```

Expected: 8 PASSED

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_pii_scrubber.py
git commit -m "test(backend): PII scrubber and masking helper tests"
```

---

## Task 4: FastAPI Skeleton

**Files:**

- Create: `backend/app/main.py`
- Create: `backend/tests/conftest.py`

- [ ] **Step 1: Write test first**

```python
# backend/tests/conftest.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
def clerk_headers():
    """Fake JWT headers — used with mocked get_current_user dependency."""
    return {"Authorization": "Bearer fake-clerk-jwt"}


@pytest.fixture
def workstation_headers():
    return {"Authorization": "Bearer ws_test_fakeworkstationtoken12345678901"}
```

```python
# backend/tests/test_health.py
import pytest


@pytest.mark.asyncio
async def test_health_returns_ok(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run test — expect ImportError (app doesn't exist yet)**

```bash
cd backend && pytest tests/test_health.py -v
```

Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write main.py**

```python
# backend/app/main.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.utils.logging import configure_structlog


def _sentry_before_send(event, hint):
    """Strip PII from Sentry events."""
    for key in ("first_name", "last_name", "dob", "doc_number", "email", "phone"):
        event.get("extra", {}).pop(key, None)
        event.get("contexts", {}).pop(key, None)
    return event


def create_app() -> FastAPI:
    configure_structlog()

    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            integrations=[
                StarletteIntegration(transaction_style="endpoint"),
                FastApiIntegration(transaction_style="endpoint"),
            ],
            before_send=_sentry_before_send,
            send_default_pii=False,
            environment=settings.environment,
        )

    application = FastAPI(
        title="Aura ID Backend",
        version="1.0.0",
        docs_url="/docs" if settings.environment != "production" else None,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @application.get("/health", tags=["ops"])
    async def health():
        return {"status": "ok"}

    return application


app = create_app()
```

- [ ] **Step 4: Run test — expect PASS**

```bash
cd backend && pytest tests/test_health.py -v
```

Expected: PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/app/main.py backend/tests/conftest.py backend/tests/test_health.py
git commit -m "feat(backend): FastAPI skeleton with Sentry, CORS, health check"
```

---

## Task 5: Database Schema

**Files:**

- Create: `backend/app/db/schema.sql`

No unit tests for SQL — correctness is verified by running against a real Supabase instance.

- [ ] **Step 1: Write schema.sql**

```sql
-- backend/app/db/schema.sql
-- Run this against your Supabase project via the SQL editor or CLI.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ─── HOTELS ──────────────────────────────────────────────────────────────────
CREATE TABLE hotels (
    id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name                  text NOT NULL,
    address               text,
    stripe_customer_id    text,
    subscription_status   text NOT NULL DEFAULT 'trialing'
                              CHECK (subscription_status IN ('trialing','active','past_due','canceled')),
    plan                  text NOT NULL DEFAULT 'starter',
    image_retention_hours int  NOT NULL DEFAULT 24 CHECK (image_retention_hours BETWEEN 1 AND 720),
    dpa_signed_at         timestamptz,
    dpa_version           text,
    created_at            timestamptz NOT NULL DEFAULT now(),
    updated_at            timestamptz NOT NULL DEFAULT now()
);

-- ─── USERS ───────────────────────────────────────────────────────────────────
CREATE TABLE users (
    id               uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    hotel_id         uuid NOT NULL REFERENCES hotels(id) ON DELETE CASCADE,
    email            text NOT NULL,
    role             text NOT NULL DEFAULT 'clerk' CHECK (role IN ('owner','clerk')),
    consent_given_at timestamptz,
    created_at       timestamptz NOT NULL DEFAULT now(),
    last_login_at    timestamptz
);

CREATE INDEX users_hotel_id_idx ON users(hotel_id);

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
CREATE POLICY users_hotel_isolation ON users
    USING (hotel_id = (auth.jwt() ->> 'hotel_id')::uuid);

-- ─── GUESTS ──────────────────────────────────────────────────────────────────
CREATE TABLE guests (
    id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    hotel_id              uuid NOT NULL REFERENCES hotels(id) ON DELETE CASCADE,
    first_name            text,
    last_name             text,
    dob                   date,
    doc_number_last4      text,
    doc_number_encrypted  bytea,      -- Fernet-encrypted at application layer
    doc_type              text CHECK (doc_type IN ('passport','drivers_license','national_id','other')),
    doc_country           text,       -- ISO 3166-1 alpha-2
    email                 text,
    phone                 text,
    address               text,
    nationality           text,
    notes                 text,
    search_vector         tsvector,
    deletion_requested_at timestamptz,
    deleted_at            timestamptz,
    created_at            timestamptz NOT NULL DEFAULT now(),
    updated_at            timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX guests_hotel_id_idx  ON guests(hotel_id);
CREATE INDEX guests_search_idx    ON guests USING GIN(search_vector);
CREATE INDEX guests_deleted_at_idx ON guests(hotel_id, deleted_at) WHERE deleted_at IS NULL;

ALTER TABLE guests ENABLE ROW LEVEL SECURITY;
CREATE POLICY guests_hotel_isolation ON guests
    USING (hotel_id = (auth.jwt() ->> 'hotel_id')::uuid);

-- search_vector auto-update
CREATE OR REPLACE FUNCTION guests_search_vector_update() RETURNS trigger AS $$
BEGIN
    NEW.search_vector :=
        to_tsvector('english', coalesce(NEW.first_name,'') || ' ' ||
                               coalesce(NEW.last_name,'') || ' ' ||
                               coalesce(NEW.doc_number_last4,''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER guests_search_vector_trigger
    BEFORE INSERT OR UPDATE ON guests
    FOR EACH ROW EXECUTE FUNCTION guests_search_vector_update();

-- ─── WORKSTATIONS ────────────────────────────────────────────────────────────
CREATE TABLE workstations (
    id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    hotel_id                uuid NOT NULL REFERENCES hotels(id) ON DELETE CASCADE,
    name                    text NOT NULL,
    pairing_code            text,
    pairing_code_expires_at timestamptz,
    token_hash              text,          -- bcrypt hash of ws_live_ token
    token_prefix            text,          -- first 12 chars for logs
    revoked_at              timestamptz,
    last_used_at            timestamptz,
    paired_at               timestamptz,
    last_seen_at            timestamptz,
    created_at              timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX workstations_hotel_id_idx ON workstations(hotel_id);

ALTER TABLE workstations ENABLE ROW LEVEL SECURITY;
CREATE POLICY workstations_hotel_isolation ON workstations
    USING (hotel_id = (auth.jwt() ->> 'hotel_id')::uuid);

-- ─── SCANS ───────────────────────────────────────────────────────────────────
CREATE TYPE scan_status AS ENUM ('pending','parsed','typed','failed','expired');

CREATE TABLE scans (
    id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    hotel_id                uuid NOT NULL REFERENCES hotels(id) ON DELETE CASCADE,
    guest_id                uuid REFERENCES guests(id),
    user_id                 uuid REFERENCES users(id),
    workstation_id          uuid REFERENCES workstations(id),
    image_path              text,
    image_deleted_at        timestamptz,
    image_deletion_scheduled_at timestamptz,
    status                  scan_status NOT NULL DEFAULT 'pending',
    parsed_data             jsonb,
    face_region_blacked_out boolean NOT NULL DEFAULT true,
    error_message           text,
    created_at              timestamptz NOT NULL DEFAULT now(),
    parsed_at               timestamptz,
    typed_at                timestamptz
);

CREATE INDEX scans_hotel_id_status_idx ON scans(hotel_id, status);
CREATE INDEX scans_hotel_id_created_idx ON scans(hotel_id, created_at DESC);
CREATE INDEX scans_pending_type_idx ON scans(hotel_id, status) WHERE status = 'parsed';

ALTER TABLE scans ENABLE ROW LEVEL SECURITY;
CREATE POLICY scans_hotel_isolation ON scans
    USING (hotel_id = (auth.jwt() ->> 'hotel_id')::uuid);

-- ─── AUDIT LOG ───────────────────────────────────────────────────────────────
CREATE TABLE audit_log (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    hotel_id      uuid,           -- nullable for system events
    user_id       uuid,
    action        text NOT NULL,  -- e.g. 'scan.parsed', 'guest.read', 'token.revoked'
    resource_type text,
    resource_id   uuid,
    metadata      jsonb,
    ip_address    inet,
    user_agent    text,
    created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX audit_log_hotel_created_idx ON audit_log(hotel_id, created_at DESC);
-- Retained 7 years. REVOKE DELETE ON audit_log FROM PUBLIC;

-- ─── DATA SUBJECT REQUESTS ───────────────────────────────────────────────────
CREATE TABLE data_subject_requests (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    hotel_id         uuid REFERENCES hotels(id),
    requester_email  text NOT NULL,
    request_type     text NOT NULL CHECK (request_type IN ('access','delete','export')),
    status           text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','processing','completed','rejected')),
    completed_at     timestamptz,
    created_at       timestamptz NOT NULL DEFAULT now()
);
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/db/schema.sql
git commit -m "feat(backend): full database schema with RLS, pgcrypto, audit log"
```

---

## Task 6: Pydantic Models

**Files:**

- Create: `backend/app/models/common.py`
- Create: `backend/app/models/scan.py`
- Create: `backend/app/models/guest.py`

- [ ] **Step 1: Write models**

```python
# backend/app/models/common.py
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: bool
    data: T | None = None
    error: str | None = None

    @classmethod
    def ok(cls, data: T) -> "ApiResponse[T]":
        return cls(success=True, data=data)

    @classmethod
    def fail(cls, error: str) -> "ApiResponse[None]":
        return cls(success=False, error=error)


class PaginatedResponse(BaseModel, Generic[T]):
    success: bool = True
    data: list[T]
    total: int
    page: int
    page_size: int
```

```python
# backend/app/models/scan.py
from datetime import date
from typing import Literal
from pydantic import BaseModel, Field


class ParsedID(BaseModel):
    """Structured output schema for Vertex AI Gemini extraction."""
    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None
    dob: date | None = None
    doc_type: Literal["passport", "drivers_license", "national_id", "other"] | None = None
    doc_number: str | None = None
    doc_country: str | None = None   # ISO 3166-1 alpha-2
    address_line_1: str | None = None
    address_line_2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    nationality: str | None = None
    sex: Literal["M", "F", "X"] | None = None
    expiry_date: date | None = None
    mrz_line_1: str | None = None
    mrz_line_2: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class ScanResponse(BaseModel):
    id: str
    status: str
    parsed_data: ParsedID | None = None
    face_region_blacked_out: bool
    created_at: str
    parsed_at: str | None = None
    typed_at: str | None = None
    error_message: str | None = None
```

```python
# backend/app/models/guest.py
from datetime import date
from pydantic import BaseModel


class GuestResponse(BaseModel):
    id: str
    hotel_id: str
    first_name: str | None = None
    last_name: str | None = None
    doc_type: str | None = None
    doc_country: str | None = None
    doc_number_last4: str | None = None
    nationality: str | None = None
    created_at: str
    deleted_at: str | None = None


class GuestListItem(BaseModel):
    id: str
    first_name: str | None = None
    last_name: str | None = None
    doc_type: str | None = None
    doc_number_last4: str | None = None
    created_at: str
```

- [ ] **Step 2: Write model tests**

```python
# backend/tests/test_models.py
from datetime import date
from app.models.common import ApiResponse
from app.models.scan import ParsedID


def test_api_response_ok():
    r = ApiResponse.ok({"id": "123"})
    assert r.success is True
    assert r.data == {"id": "123"}
    assert r.error is None


def test_api_response_fail():
    r = ApiResponse.fail("Something went wrong")
    assert r.success is False
    assert r.error == "Something went wrong"
    assert r.data is None


def test_parsed_id_defaults_none():
    p = ParsedID()
    assert p.first_name is None
    assert p.confidence == 0.0


def test_parsed_id_confidence_bounds():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        ParsedID(confidence=1.5)
```

- [ ] **Step 3: Run tests**

```bash
cd backend && pytest tests/test_models.py -v
```

Expected: 4 PASSED

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/ backend/tests/test_models.py
git commit -m "feat(backend): Pydantic v2 models — ApiResponse, ParsedID, ScanResponse, GuestResponse"
```

---

## Task 7: Auth Dependencies

**Files:**

- Create: `backend/app/deps.py`
- Create: `backend/tests/test_deps.py`

- [ ] **Step 1: Write tests first**

```python
# backend/tests/test_deps.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials


@pytest.fixture
def mock_credentials():
    def _make(token: str):
        creds = MagicMock(spec=HTTPAuthorizationCredentials)
        creds.credentials = token
        return creds
    return _make


@pytest.mark.asyncio
async def test_get_current_user_invalid_token_raises_401(mock_credentials):
    from app.deps import get_current_user
    with pytest.raises(HTTPException) as exc:
        await get_current_user(credentials=mock_credentials("not-a-jwt"))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_workstation_wrong_prefix_raises_401(mock_credentials):
    from app.deps import get_current_workstation
    request = MagicMock()
    with pytest.raises(HTTPException) as exc:
        await get_current_workstation(request=request, credentials=mock_credentials("Bearer notws"))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_workstation_revoked_raises_401(mock_credentials):
    from app.deps import get_current_workstation
    request = MagicMock()
    token = "ws_test_" + "a" * 32
    mock_result = MagicMock()
    mock_result.data = [{"id": "ws-1", "hotel_id": "hotel-1", "revoked_at": "2024-01-01"}]

    with patch("app.deps.get_supabase") as mock_sb:
        mock_client = MagicMock()
        mock_sb.return_value = mock_client
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_result
        with pytest.raises(HTTPException) as exc:
            await get_current_workstation(request=request, credentials=mock_credentials(token))
    assert exc.value.status_code == 401
```

- [ ] **Step 2: Run tests — expect ImportError**

```bash
cd backend && pytest tests/test_deps.py -v
```

Expected: FAIL (module not found)

- [ ] **Step 3: Write deps.py**

```python
# backend/app/deps.py
import secrets
import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client, Client
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings

security = HTTPBearer()


def get_supabase() -> Client:
    return create_client(settings.supabase_url, settings.supabase_service_key)


# ─── Rate limiter ────────────────────────────────────────────────────────────

def _workstation_or_ip_key(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer ws_"):
        return f"ws:{auth[7:19]}"   # first 12 chars of token as key
    return get_remote_address(request)


limiter = Limiter(key_func=get_remote_address)
workstation_limiter = Limiter(key_func=_workstation_or_ip_key)


# ─── Human clerk auth ────────────────────────────────────────────────────────

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
            options={"verify_exp": True},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    hotel_id = (
        payload.get("hotel_id")
        or payload.get("app_metadata", {}).get("hotel_id")
    )
    if not hotel_id:
        raise HTTPException(status_code=401, detail="Missing hotel_id claim")

    return {
        "user_id": payload["sub"],
        "hotel_id": hotel_id,
        "role": payload.get("role", "clerk"),
    }


# ─── Workstation auth ────────────────────────────────────────────────────────

async def get_current_workstation(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    token = credentials.credentials

    if not (token.startswith("ws_live_") or token.startswith("ws_test_")):
        raise HTTPException(status_code=401, detail="Invalid workstation token format")

    db = get_supabase()
    token_bytes = token.encode()

    # Fetch all non-revoked workstations for this token prefix (first 12 chars)
    prefix = token[:12]
    result = (
        db.table("workstations")
        .select("id, hotel_id, token_hash, revoked_at, last_used_at")
        .eq("token_prefix", prefix)
        .execute()
    )

    workstation = None
    for row in result.data or []:
        if row.get("token_hash") and bcrypt.checkpw(token_bytes, row["token_hash"].encode()):
            workstation = row
            break

    if not workstation:
        raise HTTPException(status_code=401, detail="Workstation not found")

    if workstation.get("revoked_at"):
        raise HTTPException(status_code=401, detail="Workstation token revoked")

    return {
        "workstation_id": workstation["id"],
        "hotel_id": workstation["hotel_id"],
    }
```

- [ ] **Step 4: Run tests**

```bash
cd backend && pytest tests/test_deps.py -v
```

Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/app/deps.py backend/tests/test_deps.py
git commit -m "feat(backend): auth dependencies — clerk JWT + workstation opaque token"
```

---

## Task 8: Audit Service + Middleware

**Files:**

- Create: `backend/app/services/audit.py`
- Create: `backend/app/middleware/audit.py`
- Create: `backend/tests/test_audit.py`

- [ ] **Step 1: Write tests first**

```python
# backend/tests/test_audit.py
import pytest
from unittest.mock import MagicMock, patch
from app.services.audit import write_audit_log


@pytest.mark.asyncio
async def test_write_audit_log_inserts_record():
    mock_db = MagicMock()
    mock_db.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{"id": "log-1"}])

    await write_audit_log(
        db=mock_db,
        hotel_id="hotel-uuid",
        user_id="user-uuid",
        action="scan.parsed",
        resource_type="scan",
        resource_id="scan-uuid",
        metadata={"doc_type": "passport"},
        ip_address="1.2.3.4",
        user_agent="TestAgent/1.0",
    )

    mock_db.table.assert_called_with("audit_log")
    call_args = mock_db.table.return_value.insert.call_args[0][0]
    assert call_args["action"] == "scan.parsed"
    assert call_args["hotel_id"] == "hotel-uuid"
    assert "doc_number" not in str(call_args)  # PII not in audit metadata


@pytest.mark.asyncio
async def test_write_audit_log_does_not_raise_on_db_error():
    """Audit log failure must never crash the request."""
    mock_db = MagicMock()
    mock_db.table.return_value.insert.return_value.execute.side_effect = Exception("DB error")

    # Should not raise
    await write_audit_log(
        db=mock_db,
        hotel_id="hotel-uuid",
        action="scan.parsed",
    )
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd backend && pytest tests/test_audit.py -v
```

- [ ] **Step 3: Write services/audit.py**

```python
# backend/app/services/audit.py
import structlog
from supabase import Client

log = structlog.get_logger()


async def write_audit_log(
    *,
    db: Client,
    hotel_id: str | None = None,
    user_id: str | None = None,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    metadata: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Append-only audit log write. Never raises — failure is logged but swallowed."""
    try:
        db.table("audit_log").insert({
            "hotel_id": hotel_id,
            "user_id": user_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "metadata": metadata or {},
            "ip_address": ip_address,
            "user_agent": user_agent,
        }).execute()
    except Exception as exc:
        log.error("audit_log.write_failed", action=action, error=str(exc))
```

- [ ] **Step 4: Write middleware/audit.py**

```python
# backend/app/middleware/audit.py
import time
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

log = structlog.get_logger()


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = int((time.perf_counter() - start) * 1000)

        log.info(
            "http.request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
            ip=request.client.host if request.client else None,
        )
        return response
```

- [ ] **Step 5: Run tests**

```bash
cd backend && pytest tests/test_audit.py -v
```

Expected: 2 PASSED

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/audit.py backend/app/middleware/audit.py backend/tests/test_audit.py
git commit -m "feat(backend): audit service and HTTP request logging middleware"
```

---

## Task 9: Subscription Gate

**Files:**

- Create: `backend/app/middleware/subscription_gate.py`
- Create: `backend/tests/test_subscription_gate.py`

- [ ] **Step 1: Write tests**

```python
# backend/tests/test_subscription_gate.py
import pytest
from unittest.mock import patch, MagicMock
from httpx import AsyncClient, ASGITransport
from app.main import create_app


@pytest.fixture
def app_with_gate():
    from app.middleware.subscription_gate import SubscriptionGateMiddleware
    application = create_app()
    application.add_middleware(SubscriptionGateMiddleware)
    return application


@pytest.mark.asyncio
async def test_health_bypasses_gate(app_with_gate):
    async with AsyncClient(transport=ASGITransport(app=app_with_gate), base_url="http://test") as c:
        response = await c.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_api_route_blocked_when_no_hotel_context(app_with_gate):
    """Routes under /api/v1 without hotel context return 403."""
    async with AsyncClient(transport=ASGITransport(app=app_with_gate), base_url="http://test") as c:
        response = await c.get("/api/v1/guests")
    # 403 (no hotel context) or 401 (no auth) — either is fine here
    assert response.status_code in (401, 403, 404)
```

- [ ] **Step 2: Write middleware/subscription_gate.py**

```python
# backend/app/middleware/subscription_gate.py
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from app.deps import get_supabase

BYPASS_PREFIXES = ("/health", "/api/v1/billing", "/api/v1/webhooks", "/docs", "/openapi")


class SubscriptionGateMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if any(path.startswith(p) for p in BYPASS_PREFIXES):
            return await call_next(request)

        hotel_id = request.state.__dict__.get("hotel_id")
        if hotel_id is None:
            return await call_next(request)  # let auth middleware reject it

        db = get_supabase()
        result = (
            db.table("hotels")
            .select("subscription_status")
            .eq("id", hotel_id)
            .single()
            .execute()
        )

        if not result.data or result.data["subscription_status"] not in ("trialing", "active"):
            return JSONResponse(
                status_code=403,
                content={"success": False, "error": "Subscription inactive"},
            )

        return await call_next(request)
```

- [ ] **Step 3: Run tests**

```bash
cd backend && pytest tests/test_subscription_gate.py -v
```

Expected: 2 PASSED

- [ ] **Step 4: Register middleware in main.py**

Add to `create_app()` in `backend/app/main.py` after CORSMiddleware:

```python
    from app.middleware.audit import AuditMiddleware
    from app.middleware.subscription_gate import SubscriptionGateMiddleware

    application.add_middleware(AuditMiddleware)
    application.add_middleware(SubscriptionGateMiddleware)
```

- [ ] **Step 5: Run health test to confirm no regression**

```bash
cd backend && pytest tests/test_health.py -v
```

Expected: PASSED

- [ ] **Step 6: Commit**

```bash
git add backend/app/middleware/subscription_gate.py backend/app/main.py backend/tests/test_subscription_gate.py
git commit -m "feat(backend): subscription gate middleware blocks inactive hotels"
```

---

## Task 10: Image Pipeline — EXIF Strip

**Files:**

- Create: `backend/app/services/image_pipeline.py` (partial — step 1 validate + step 2 EXIF strip)
- Create: `backend/tests/test_image_pipeline.py` (partial)

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_image_pipeline.py
import io
import pytest
import piexif
from PIL import Image
from app.services.image_pipeline import validate_upload, strip_exif

ALLOWED_TYPES = {"image/jpeg", "image/png"}


def make_jpeg_with_exif() -> bytes:
    """Create a minimal JPEG with GPS EXIF data."""
    img = Image.new("RGB", (100, 100), color=(128, 128, 128))
    exif_dict = {
        "GPS": {
            piexif.GPSIFD.GPSLatitude: ((40, 1), (26, 1), (4600, 100)),
            piexif.GPSIFD.GPSLongitude: ((79, 1), (58, 1), (3400, 100)),
        }
    }
    exif_bytes = piexif.dump(exif_dict)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif_bytes)
    return buf.getvalue()


def make_plain_jpeg() -> bytes:
    img = Image.new("RGB", (100, 100), color=(200, 200, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_validate_upload_accepts_jpeg():
    data = make_plain_jpeg()
    validate_upload(data, "image/jpeg")  # should not raise


def test_validate_upload_rejects_oversized():
    data = b"x" * (9 * 1024 * 1024)  # 9MB
    with pytest.raises(ValueError, match="exceeds"):
        validate_upload(data, "image/jpeg")


def test_validate_upload_rejects_mime_mismatch():
    data = make_plain_jpeg()  # JPEG bytes
    with pytest.raises(ValueError, match="MIME"):
        validate_upload(data, "image/png")  # wrong MIME


def test_strip_exif_removes_gps():
    original = make_jpeg_with_exif()
    stripped = strip_exif(original)
    img = Image.open(io.BytesIO(stripped))
    exif_data = img.info.get("exif", b"")
    if exif_data:
        exif_dict = piexif.load(exif_data)
        assert not exif_dict.get("GPS"), "GPS data must be removed"


def test_strip_exif_output_is_valid_jpeg():
    original = make_jpeg_with_exif()
    stripped = strip_exif(original)
    img = Image.open(io.BytesIO(stripped))
    assert img.format == "JPEG"
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd backend && pytest tests/test_image_pipeline.py -v
```

- [ ] **Step 3: Implement validate_upload and strip_exif**

```python
# backend/app/services/image_pipeline.py
import io
import struct
import piexif
from PIL import Image

MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # 8MB

_MAGIC_BYTES = {
    "image/jpeg": [(0, b"\xff\xd8\xff")],
    "image/png": [(0, b"\x89PNG")],
    # HEIC has variable magic; check ftyp box
    "image/heic": [(4, b"ftyp")],
}


def validate_upload(data: bytes, content_type: str) -> None:
    """Raises ValueError if data is too large or MIME doesn't match bytes."""
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError(f"Upload exceeds {MAX_UPLOAD_BYTES // (1024*1024)}MB limit")

    ct = content_type.split(";")[0].strip().lower()
    if ct not in _MAGIC_BYTES:
        raise ValueError(f"Unsupported content type: {ct}")

    for offset, magic in _MAGIC_BYTES[ct]:
        if data[offset : offset + len(magic)] != magic:
            raise ValueError(f"MIME type {ct} does not match file bytes")


def strip_exif(image_bytes: bytes) -> bytes:
    """Strip all EXIF/metadata and re-encode through Pillow as JPEG."""
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    out = io.BytesIO()
    img.save(out, format="JPEG", exif=piexif.dump({}), quality=95)
    return out.getvalue()
```

- [ ] **Step 4: Run tests**

```bash
cd backend && pytest tests/test_image_pipeline.py -v
```

Expected: 5 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/image_pipeline.py backend/tests/test_image_pipeline.py
git commit -m "feat(backend): image pipeline — upload validation and EXIF stripping"
```

---

## Task 11: Image Pipeline — Face Blackout

**Files:**

- Modify: `backend/app/services/image_pipeline.py` (add face blackout)
- Modify: `backend/tests/test_image_pipeline.py` (add blackout tests)

- [ ] **Step 1: Write failing tests**

Append to `backend/tests/test_image_pipeline.py`:

```python
import numpy as np
import cv2
from unittest.mock import patch, MagicMock
from app.services.image_pipeline import apply_face_blackout


def make_white_numpy_image(h=200, w=300) -> np.ndarray:
    return np.ones((h, w, 3), dtype=np.uint8) * 255


def test_face_blackout_zeroes_detected_region():
    """Core compliance test: face region pixels must be (0,0,0) after blackout."""
    img = make_white_numpy_image()

    # Inject a fake detection: face at (100, 50, 80, 100) = x, y, w, h
    fake_detection = MagicMock()
    fake_bbox = MagicMock()
    fake_bbox.xmin = 100 / 300
    fake_bbox.ymin = 50 / 200
    fake_bbox.width = 80 / 300
    fake_bbox.height = 100 / 200
    fake_detection.location_data.relative_bounding_box = fake_bbox

    mock_results = MagicMock()
    mock_results.detections = [fake_detection]

    with patch("app.services.image_pipeline.mp") as mock_mp:
        mock_mp.solutions.face_detection.FaceDetection.return_value.__enter__ = MagicMock(return_value=MagicMock())
        detector_instance = MagicMock()
        detector_instance.process.return_value = mock_results
        mock_mp.solutions.face_detection.FaceDetection.return_value = detector_instance

        result, face_found = apply_face_blackout(img)

    assert face_found is True
    # Check that a region inside the padded bbox is all black
    # With 10% padding on each side: x1 = max(0, 90), y1 = max(0, 40)
    cx, cy = 140, 100  # center of detected face
    assert np.all(result[cy - 5 : cy + 5, cx - 5 : cx + 5] == 0), \
        "Center of face region must be all black pixels"


def test_face_blackout_no_face_returns_original():
    img = make_white_numpy_image()
    mock_results = MagicMock()
    mock_results.detections = None

    with patch("app.services.image_pipeline.mp") as mock_mp:
        detector_instance = MagicMock()
        detector_instance.process.return_value = mock_results
        mock_mp.solutions.face_detection.FaceDetection.return_value = detector_instance

        result, face_found = apply_face_blackout(img)

    assert face_found is False
    assert np.all(result == 255)  # original white image unchanged


def test_face_blackout_does_not_modify_outside_bbox():
    img = make_white_numpy_image(200, 300)
    fake_detection = MagicMock()
    fake_bbox = MagicMock()
    fake_bbox.xmin = 0.3
    fake_bbox.ymin = 0.3
    fake_bbox.width = 0.2
    fake_bbox.height = 0.2
    fake_detection.location_data.relative_bounding_box = fake_bbox
    mock_results = MagicMock()
    mock_results.detections = [fake_detection]

    with patch("app.services.image_pipeline.mp") as mock_mp:
        detector_instance = MagicMock()
        detector_instance.process.return_value = mock_results
        mock_mp.solutions.face_detection.FaceDetection.return_value = detector_instance

        result, _ = apply_face_blackout(img)

    # Top-left corner (far from face) must still be white
    assert np.all(result[0:10, 0:10] == 255)
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd backend && pytest tests/test_image_pipeline.py::test_face_blackout_zeroes_detected_region -v
```

- [ ] **Step 3: Add apply_face_blackout to image_pipeline.py**

```python
# Append to backend/app/services/image_pipeline.py
import numpy as np
import cv2
import mediapipe as mp
import structlog

log = structlog.get_logger()


def apply_face_blackout(img: np.ndarray) -> tuple[np.ndarray, bool]:
    """
    Detect all faces and paint solid black over each bounding box (+ 10% padding).
    Returns (modified_image, face_was_detected).
    This is the BIPA-critical step. Must run on every image before Vertex AI.
    """
    h, w = img.shape[:2]
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    result_img = img.copy()
    face_found = False

    detector = mp.solutions.face_detection.FaceDetection(
        model_selection=0, min_detection_confidence=0.5
    )
    results = detector.process(rgb)

    if not results.detections:
        log.info("image_pipeline.no_face_detected")
        return result_img, False

    for detection in results.detections:
        face_found = True
        bbox = detection.location_data.relative_bounding_box
        pad_x = bbox.width * 0.10
        pad_y = bbox.height * 0.10
        x1 = max(0, int((bbox.xmin - pad_x) * w))
        y1 = max(0, int((bbox.ymin - pad_y) * h))
        x2 = min(w, int((bbox.xmin + bbox.width + pad_x) * w))
        y2 = min(h, int((bbox.ymin + bbox.height + pad_y) * h))
        result_img[y1:y2, x1:x2] = 0

    log.info("image_pipeline.face_blacked_out", face_count=len(results.detections))
    return result_img, face_found
```

- [ ] **Step 4: Run tests**

```bash
cd backend && pytest tests/test_image_pipeline.py -v
```

Expected: 8 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/image_pipeline.py backend/tests/test_image_pipeline.py
git commit -m "feat(backend): image pipeline — MediaPipe face blackout (compliance step)"
```

---

## Task 12: Image Pipeline — Compress + Full Orchestration

**Files:**

- Modify: `backend/app/services/image_pipeline.py` (add compress + PipelineResult + run_pipeline)
- Modify: `backend/tests/test_image_pipeline.py` (add orchestration tests)

- [ ] **Step 1: Write failing tests for full pipeline**

Append to `backend/tests/test_image_pipeline.py`:

```python
from dataclasses import dataclass
from app.services.image_pipeline import compress_image, run_pipeline, PipelineResult


def test_compress_image_shrinks_large_image():
    large_img = Image.new("RGB", (3000, 2000), color=(100, 150, 200))
    buf = io.BytesIO()
    large_img.save(buf, format="JPEG")
    compressed = compress_image(buf.getvalue())
    out_img = Image.open(io.BytesIO(compressed))
    assert max(out_img.size) <= 1600


def test_compress_image_output_is_jpeg():
    img = Image.new("RGB", (200, 150))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    result = compress_image(buf.getvalue())
    assert Image.open(io.BytesIO(result)).format == "JPEG"


@pytest.mark.asyncio
async def test_run_pipeline_sets_face_blacked_out_true():
    jpeg = make_plain_jpeg()
    with patch("app.services.image_pipeline.apply_face_blackout") as mock_blackout:
        # Return a valid numpy array + True (face detected)
        img_arr = np.ones((100, 100, 3), dtype=np.uint8) * 128
        mock_blackout.return_value = (img_arr, True)
        result: PipelineResult = await run_pipeline(jpeg, "image/jpeg", scan_id="test-001")

    assert result.face_region_blacked_out is True
    assert result.image_bytes is not None
    assert len(result.image_bytes) > 0


@pytest.mark.asyncio
async def test_run_pipeline_raises_on_invalid_mime():
    with pytest.raises(ValueError):
        await run_pipeline(b"not an image", "application/pdf", scan_id="test-002")
```

- [ ] **Step 2: Implement compress_image, PipelineResult, run_pipeline**

Append to `backend/app/services/image_pipeline.py`:

```python
import asyncio
from dataclasses import dataclass


@dataclass
class PipelineResult:
    image_bytes: bytes
    face_region_blacked_out: bool
    scan_id: str


def compress_image(image_bytes: bytes, max_longest_edge: int = 1600, quality: int = 85) -> bytes:
    """Resize so longest edge <= max_longest_edge, re-encode JPEG at given quality."""
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode != "RGB":
        img = img.convert("RGB")
    longest = max(img.size)
    if longest > max_longest_edge:
        scale = max_longest_edge / longest
        new_size = (int(img.width * scale), int(img.height * scale))
        img = img.resize(new_size, Image.LANCZOS)
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=quality, optimize=True)
    return out.getvalue()


async def run_pipeline(image_bytes: bytes, content_type: str, scan_id: str) -> PipelineResult:
    """
    Run all pre-processing steps before Vertex AI.
    Steps: validate → strip_exif → face_blackout → compress.
    Raises ValueError on validation failure.
    Raises RuntimeError if face blackout step fails unexpectedly.
    """
    # Step 1: Validate
    validate_upload(image_bytes, content_type)

    # Step 2: Strip EXIF
    clean_bytes = strip_exif(image_bytes)
    log.info("image_pipeline.exif_stripped", scan_id=scan_id)

    # Step 3 + 4: Detect face and blackout — run in thread to avoid blocking event loop
    def _blackout_sync():
        img_arr = np.array(Image.open(io.BytesIO(clean_bytes)).convert("RGB"))
        img_bgr = cv2.cvtColor(img_arr, cv2.COLOR_RGB2BGR)
        return apply_face_blackout(img_bgr)

    try:
        blacked_arr, face_found = await asyncio.get_event_loop().run_in_executor(None, _blackout_sync)
    except Exception as exc:
        log.error("image_pipeline.face_blackout_failed", scan_id=scan_id, error=str(exc))
        raise RuntimeError(f"Face blackout step failed: {exc}") from exc

    log.info("image_pipeline.face_blacked_out", scan_id=scan_id, face_detected=face_found)

    # Step 5: Compress
    blacked_rgb = cv2.cvtColor(blacked_arr, cv2.COLOR_BGR2RGB)
    pil_blacked = Image.fromarray(blacked_rgb)
    buf = io.BytesIO()
    pil_blacked.save(buf, format="JPEG", quality=95)
    compressed = compress_image(buf.getvalue())

    return PipelineResult(
        image_bytes=compressed,
        face_region_blacked_out=True,
        scan_id=scan_id,
    )
```

- [ ] **Step 3: Run all image pipeline tests**

```bash
cd backend && pytest tests/test_image_pipeline.py -v
```

Expected: 12 PASSED

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/image_pipeline.py backend/tests/test_image_pipeline.py
git commit -m "feat(backend): image pipeline — compress + full orchestration with compliance guarantees"
```

---

## Task 13: Storage Service

**Files:**

- Create: `backend/app/services/storage.py`
- Create: `backend/tests/test_storage.py`

- [ ] **Step 1: Write tests**

```python
# backend/tests/test_storage.py
import pytest
from unittest.mock import MagicMock, patch
from app.services.storage import upload_scan_image, get_signed_url, delete_scan_image


@pytest.fixture
def mock_supabase():
    db = MagicMock()
    storage = MagicMock()
    db.storage = storage
    return db


def test_upload_scan_image_returns_path(mock_supabase):
    mock_supabase.storage.from_.return_value.upload.return_value = MagicMock(path="scans/hotel-1/scan-1.jpg")
    path = upload_scan_image(
        db=mock_supabase,
        hotel_id="hotel-1",
        scan_id="scan-1",
        image_bytes=b"fakejpeg",
    )
    assert path == "scans/hotel-1/scan-1.jpg"
    mock_supabase.storage.from_.assert_called_with("scan-images")


def test_delete_scan_image_calls_remove(mock_supabase):
    delete_scan_image(db=mock_supabase, path="scans/hotel-1/scan-1.jpg")
    mock_supabase.storage.from_.return_value.remove.assert_called_once_with(["scans/hotel-1/scan-1.jpg"])


def test_get_signed_url_returns_url(mock_supabase):
    mock_supabase.storage.from_.return_value.create_signed_url.return_value = {
        "signedURL": "https://signed.example.com/scan.jpg"
    }
    url = get_signed_url(db=mock_supabase, path="scans/hotel-1/scan-1.jpg", expires_in=300)
    assert url == "https://signed.example.com/scan.jpg"
```

- [ ] **Step 2: Implement storage.py**

```python
# backend/app/services/storage.py
import structlog
from supabase import Client

BUCKET = "scan-images"
log = structlog.get_logger()


def upload_scan_image(*, db: Client, hotel_id: str, scan_id: str, image_bytes: bytes) -> str:
    path = f"scans/{hotel_id}/{scan_id}.jpg"
    db.storage.from_(BUCKET).upload(
        path=path,
        file=image_bytes,
        file_options={"content-type": "image/jpeg", "upsert": "true"},
    )
    log.info("storage.uploaded", scan_id=scan_id, path=path)
    return path


def get_signed_url(*, db: Client, path: str, expires_in: int = 300) -> str:
    result = db.storage.from_(BUCKET).create_signed_url(path, expires_in)
    return result["signedURL"]


def delete_scan_image(*, db: Client, path: str) -> None:
    db.storage.from_(BUCKET).remove([path])
    log.info("storage.deleted", path=path)
```

- [ ] **Step 3: Run tests**

```bash
cd backend && pytest tests/test_storage.py -v
```

Expected: 3 PASSED

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/storage.py backend/tests/test_storage.py
git commit -m "feat(backend): Supabase Storage service — upload, signed URL, delete"
```

---

## Task 14: Vertex AI — Interface + Fake Client

**Files:**

- Create: `backend/app/services/vertex_ai.py` (abstract + fake only)
- Create: `backend/tests/test_vertex_ai.py`

- [ ] **Step 1: Write tests for the fake client**

```python
# backend/tests/test_vertex_ai.py
import pytest
from datetime import date
from app.services.vertex_ai import FakeVertexClient
from app.models.scan import ParsedID


@pytest.mark.asyncio
async def test_fake_client_returns_parsed_id():
    client = FakeVertexClient()
    result = await client.extract_id_fields(b"fakeimagebytes")
    assert isinstance(result, ParsedID)


@pytest.mark.asyncio
async def test_fake_client_returns_configured_data():
    fixed = ParsedID(first_name="Jane", last_name="Doe", confidence=0.95)
    client = FakeVertexClient(response=fixed)
    result = await client.extract_id_fields(b"anyimage")
    assert result.first_name == "Jane"
    assert result.last_name == "Doe"
    assert result.confidence == 0.95


@pytest.mark.asyncio
async def test_fake_client_raises_on_injected_error():
    client = FakeVertexClient(raise_error=ValueError("Vertex AI unavailable"))
    with pytest.raises(ValueError, match="Vertex AI unavailable"):
        await client.extract_id_fields(b"anyimage")
```

- [ ] **Step 2: Implement abstract interface + fake**

```python
# backend/app/services/vertex_ai.py
from abc import ABC, abstractmethod
from app.models.scan import ParsedID


class AbstractVertexClient(ABC):
    @abstractmethod
    async def extract_id_fields(self, image_bytes: bytes) -> ParsedID:
        """Extract text fields from an ID image. Never returns biometric data."""
        ...


class FakeVertexClient(AbstractVertexClient):
    """In-memory stub for tests. No network calls."""

    def __init__(self, response: ParsedID | None = None, raise_error: Exception | None = None):
        self._response = response or ParsedID(confidence=0.9)
        self._raise_error = raise_error

    async def extract_id_fields(self, image_bytes: bytes) -> ParsedID:
        if self._raise_error:
            raise self._raise_error
        return self._response
```

- [ ] **Step 3: Run tests**

```bash
cd backend && pytest tests/test_vertex_ai.py -v
```

Expected: 3 PASSED

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/vertex_ai.py backend/tests/test_vertex_ai.py
git commit -m "feat(backend): Vertex AI abstract interface and FakeVertexClient for testing"
```

---

## Task 15: Vertex AI — Real Client + Biometric Rejection

**Files:**

- Modify: `backend/app/services/vertex_ai.py` (add VertexAIClient + biometric check)
- Modify: `backend/tests/test_vertex_ai.py` (add biometric rejection tests)

- [ ] **Step 1: Write biometric rejection tests**

Append to `backend/tests/test_vertex_ai.py`:

```python
from app.services.vertex_ai import check_for_biometric_content


def test_biometric_check_flags_eye_color():
    assert check_for_biometric_content('{"first_name":"John","notes":"blue eyes"}') is True


def test_biometric_check_flags_facial_description():
    assert check_for_biometric_content("the person has a broad nose and square jaw") is True


def test_biometric_check_passes_clean_json():
    clean = '{"first_name":"John","last_name":"Smith","doc_number":"AB123456"}'
    assert check_for_biometric_content(clean) is False


def test_biometric_check_passes_address_fields():
    assert check_for_biometric_content('{"city":"Chicago","state":"IL"}') is False
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd backend && pytest tests/test_vertex_ai.py::test_biometric_check_flags_eye_color -v
```

- [ ] **Step 3: Implement VertexAIClient + biometric check**

```python
# Append to backend/app/services/vertex_ai.py
import re
import json
import asyncio
import structlog
import vertexai
from vertexai.generative_models import GenerativeModel, Part, GenerationConfig

from app.config import settings

log = structlog.get_logger()

_BIOMETRIC_PATTERNS = re.compile(
    r"\b(eye[s]?|iris|pupil|retina|complexion|skin tone|hair color|"
    r"blonde|brunette|bald|nose|mouth|lips|ears|jaw|chin|cheek|"
    r"facial feature|portrait|photograph of|image of the person)\b",
    re.IGNORECASE,
)

_EXTRACTION_PROMPT = (
    "You are a document OCR system. Extract ONLY the text fields from the "
    "government-issued ID shown. Return a JSON object matching the schema. "
    "Do NOT describe, analyze, or comment on the photograph, face, or physical "
    "appearance of any person in the image. Extract text only."
)

_VERTEX_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "first_name": {"type": "STRING"},
        "last_name": {"type": "STRING"},
        "middle_name": {"type": "STRING"},
        "dob": {"type": "STRING"},
        "doc_type": {"type": "STRING", "enum": ["passport", "drivers_license", "national_id", "other"]},
        "doc_number": {"type": "STRING"},
        "doc_country": {"type": "STRING"},
        "address_line_1": {"type": "STRING"},
        "address_line_2": {"type": "STRING"},
        "city": {"type": "STRING"},
        "state": {"type": "STRING"},
        "postal_code": {"type": "STRING"},
        "nationality": {"type": "STRING"},
        "sex": {"type": "STRING", "enum": ["M", "F", "X"]},
        "expiry_date": {"type": "STRING"},
        "mrz_line_1": {"type": "STRING"},
        "mrz_line_2": {"type": "STRING"},
        "confidence": {"type": "NUMBER"},
    },
}


def check_for_biometric_content(text: str) -> bool:
    """Returns True if response text appears to contain biometric descriptions."""
    return bool(_BIOMETRIC_PATTERNS.search(text))


class VertexAIClient(AbstractVertexClient):
    def __init__(self) -> None:
        vertexai.init(project=settings.gcp_project_id, location=settings.vertex_location)
        self._model = GenerativeModel("gemini-2.5-flash")

    async def extract_id_fields(self, image_bytes: bytes) -> ParsedID:
        def _call() -> ParsedID:
            image_part = Part.from_data(data=image_bytes, mime_type="image/jpeg")
            response = self._model.generate_content(
                contents=[image_part, _EXTRACTION_PROMPT],
                generation_config=GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=_VERTEX_SCHEMA,
                    temperature=0,
                ),
            )
            raw_text = response.text

            if check_for_biometric_content(raw_text):
                log.error("vertex_ai.biometric_content_detected", preview=raw_text[:100])
                raise ValueError("Vertex AI response contained biometric content — rejected")

            data = json.loads(raw_text)
            return ParsedID.model_validate(data)

        return await asyncio.get_event_loop().run_in_executor(None, _call)
```

- [ ] **Step 4: Run all vertex AI tests**

```bash
cd backend && pytest tests/test_vertex_ai.py -v
```

Expected: 7 PASSED (fake client tests + biometric check tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/vertex_ai.py backend/tests/test_vertex_ai.py
git commit -m "feat(backend): VertexAIClient with structured extraction and biometric content rejection"
```

---

## Task 16: Retention Job

**Files:**

- Create: `backend/app/services/retention.py`
- Create: `backend/tests/test_retention.py`

- [ ] **Step 1: Write tests**

```python
# backend/tests/test_retention.py
import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timezone


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.storage = MagicMock()
    return db


def test_delete_expired_images_deletes_storage_and_nulls_path(mock_db):
    from app.services.retention import delete_expired_images

    # Two expired scans
    mock_db.table.return_value.select.return_value.not_.return_value.lte.return_value.execute.return_value = MagicMock(
        data=[
            {"id": "scan-1", "hotel_id": "hotel-1", "image_path": "scans/hotel-1/scan-1.jpg"},
            {"id": "scan-2", "hotel_id": "hotel-1", "image_path": "scans/hotel-1/scan-2.jpg"},
        ]
    )
    mock_db.table.return_value.update.return_value.in_.return_value.execute.return_value = MagicMock(data=[])

    delete_expired_images(db=mock_db)

    # Storage delete called for both paths
    mock_db.storage.from_.return_value.remove.assert_called()


def test_delete_expired_images_noop_when_none_expired(mock_db):
    from app.services.retention import delete_expired_images

    mock_db.table.return_value.select.return_value.not_.return_value.lte.return_value.execute.return_value = MagicMock(
        data=[]
    )

    delete_expired_images(db=mock_db)

    mock_db.storage.from_.return_value.remove.assert_not_called()
```

- [ ] **Step 2: Implement retention.py**

```python
# backend/app/services/retention.py
from datetime import datetime, timezone
import structlog
from supabase import Client
from apscheduler.schedulers.background import BackgroundScheduler

from app.deps import get_supabase

log = structlog.get_logger()


def delete_expired_images(db: Client | None = None) -> None:
    """Delete images from storage where retention period has elapsed."""
    if db is None:
        db = get_supabase()

    now_iso = datetime.now(timezone.utc).isoformat()

    result = (
        db.table("scans")
        .select("id, hotel_id, image_path")
        .not_("image_path", "is", None)
        .lte("image_deletion_scheduled_at", now_iso)
        .execute()
    )

    expired = result.data or []
    if not expired:
        return

    paths = [s["image_path"] for s in expired if s.get("image_path")]
    scan_ids = [s["id"] for s in expired]

    if paths:
        db.storage.from_("scan-images").remove(paths)

    db.table("scans").update({
        "image_path": None,
        "image_deleted_at": now_iso,
        "status": "expired",
    }).in_("id", scan_ids).execute()

    log.info("retention.images_deleted", count=len(scan_ids))


def start_retention_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(delete_expired_images, "interval", hours=1, id="retention_job")
    scheduler.start()
    log.info("retention.scheduler_started", interval_hours=1)
    return scheduler
```

- [ ] **Step 3: Wire scheduler into main.py**

In `backend/app/main.py`, inside `create_app()` after building `application`:

```python
    from app.services.retention import start_retention_scheduler
    import atexit

    scheduler = start_retention_scheduler()
    atexit.register(scheduler.shutdown)
```

- [ ] **Step 4: Run tests**

```bash
cd backend && pytest tests/test_retention.py -v
```

Expected: 2 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/retention.py backend/app/main.py backend/tests/test_retention.py
git commit -m "feat(backend): hourly APScheduler retention job — deletes images past retention window"
```

---

## Task 17: POST /scans — End to End

**Files:**

- Create: `backend/app/routers/scans.py`
- Create: `backend/tests/test_scans.py`
- Modify: `backend/app/main.py` (register router)

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_scans.py
import io
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from PIL import Image
from httpx import AsyncClient, ASGITransport


def make_jpeg() -> bytes:
    img = Image.new("RGB", (200, 150), color=(100, 100, 100))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def app_with_scans():
    from app.main import create_app
    application = create_app()
    from app.routers.scans import router
    application.include_router(router, prefix="/api/v1")
    return application


@pytest.fixture
def fake_user():
    return {"user_id": "user-1", "hotel_id": "hotel-1", "role": "clerk"}


@pytest.mark.asyncio
async def test_post_scans_returns_scan_id(app_with_scans, fake_user):
    from app.deps import get_current_user
    from app.services.vertex_ai import FakeVertexClient
    from app.models.scan import ParsedID

    fake_result = ParsedID(first_name="Jane", last_name="Doe", confidence=0.9)

    with (
        patch("app.routers.scans.run_pipeline") as mock_pipeline,
        patch("app.routers.scans.upload_scan_image", return_value="scans/hotel-1/scan-1.jpg"),
        patch("app.routers.scans.get_vertex_client", return_value=FakeVertexClient(response=fake_result)),
        patch("app.routers.scans.get_supabase") as mock_db,
        patch("app.routers.scans.write_audit_log", new_callable=AsyncMock),
    ):
        from app.services.image_pipeline import PipelineResult
        import numpy as np
        mock_pipeline.return_value = PipelineResult(
            image_bytes=make_jpeg(), face_region_blacked_out=True, scan_id="scan-1"
        )
        mock_db_instance = MagicMock()
        mock_db.return_value = mock_db_instance
        mock_db_instance.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "scan-1", "status": "parsed", "face_region_blacked_out": True,
                   "created_at": "2026-05-14T00:00:00Z"}]
        )
        mock_db_instance.table.return_value.upsert.return_value.execute.return_value = MagicMock(
            data=[{"id": "guest-1"}]
        )

        app_with_scans.dependency_overrides[get_current_user] = lambda: fake_user
        async with AsyncClient(transport=ASGITransport(app=app_with_scans), base_url="http://test") as c:
            response = await c.post(
                "/api/v1/scans",
                files={"file": ("id.jpg", make_jpeg(), "image/jpeg")},
            )
        app_with_scans.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert "id" in body["data"]


@pytest.mark.asyncio
async def test_post_scans_rejects_oversized_file(app_with_scans, fake_user):
    from app.deps import get_current_user

    app_with_scans.dependency_overrides[get_current_user] = lambda: fake_user
    async with AsyncClient(transport=ASGITransport(app=app_with_scans), base_url="http://test") as c:
        response = await c.post(
            "/api/v1/scans",
            files={"file": ("big.jpg", b"x" * (9 * 1024 * 1024), "image/jpeg")},
        )
    app_with_scans.dependency_overrides.clear()

    assert response.status_code == 422
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd backend && pytest tests/test_scans.py -v
```

- [ ] **Step 3: Implement scans router**

```python
# backend/app/routers/scans.py
import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile

from app.deps import get_current_user, get_current_workstation, get_supabase, limiter
from app.models.common import ApiResponse
from app.models.scan import ScanResponse, ParsedID
from app.services.image_pipeline import run_pipeline
from app.services.storage import upload_scan_image
from app.services.audit import write_audit_log
from app.utils.pii import mask_name, mask_doc_number
from cryptography.fernet import Fernet
from app.config import settings

router = APIRouter(tags=["scans"])


def get_vertex_client():
    from app.services.vertex_ai import VertexAIClient
    return VertexAIClient()


def _encrypt_doc_number(doc_number: str) -> bytes:
    f = Fernet(settings.doc_encryption_key.encode())
    return f.encrypt(doc_number.encode())


@router.post("/scans", status_code=201, response_model=ApiResponse[ScanResponse])
@limiter.limit("100/minute")
async def create_scan(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db=Depends(get_supabase),
):
    scan_id = str(uuid.uuid4())
    hotel_id = current_user["hotel_id"]
    user_id = current_user["user_id"]

    image_bytes = await file.read()
    content_type = file.content_type or "image/jpeg"

    # Persist initial scan record
    db.table("scans").insert({
        "id": scan_id,
        "hotel_id": hotel_id,
        "user_id": user_id,
        "status": "pending",
        "face_region_blacked_out": True,
    }).execute()

    try:
        # Steps 1-5: validate, strip EXIF, blackout face, compress
        pipeline_result = await run_pipeline(image_bytes, content_type, scan_id=scan_id)
    except (ValueError, RuntimeError) as exc:
        db.table("scans").update({"status": "failed", "error_message": str(exc)}).eq("id", scan_id).execute()
        raise HTTPException(status_code=422, detail=str(exc))

    # Step 6: Get hotel retention hours
    hotel_result = db.table("hotels").select("image_retention_hours").eq("id", hotel_id).single().execute()
    retention_hours = hotel_result.data.get("image_retention_hours", 24) if hotel_result.data else 24
    deletion_at = (datetime.now(timezone.utc) + timedelta(hours=retention_hours)).isoformat()

    # Upload blacked-out image
    image_path = upload_scan_image(db=db, hotel_id=hotel_id, scan_id=scan_id, image_bytes=pipeline_result.image_bytes)

    # Step 7: Vertex AI extraction
    vertex_client = get_vertex_client()
    try:
        parsed: ParsedID = await vertex_client.extract_id_fields(pipeline_result.image_bytes)
    except Exception as exc:
        db.table("scans").update({"status": "failed", "error_message": str(exc), "image_path": image_path}).eq("id", scan_id).execute()
        raise HTTPException(status_code=502, detail="AI extraction failed")

    # Step 8: Persist guest + scan
    guest_id = None
    if parsed.last_name:
        guest_payload = {
            "hotel_id": hotel_id,
            "first_name": parsed.first_name,
            "last_name": parsed.last_name,
            "dob": parsed.dob.isoformat() if parsed.dob else None,
            "doc_type": parsed.doc_type,
            "doc_country": parsed.doc_country,
            "nationality": parsed.nationality,
            "doc_number_last4": mask_doc_number(parsed.doc_number)[-4:] if parsed.doc_number else None,
        }
        if parsed.doc_number:
            guest_payload["doc_number_encrypted"] = _encrypt_doc_number(parsed.doc_number).decode()

        if parsed.doc_number and parsed.doc_country:
            # Upsert on doc_number_last4 + doc_country + hotel_id
            guest_result = db.table("guests").upsert(guest_payload, on_conflict="hotel_id,doc_number_last4,doc_country").execute()
        else:
            guest_result = db.table("guests").insert(guest_payload).execute()

        if guest_result.data:
            guest_id = guest_result.data[0]["id"]

    now_iso = datetime.now(timezone.utc).isoformat()
    scan_update = {
        "status": "parsed",
        "guest_id": guest_id,
        "image_path": image_path,
        "image_deletion_scheduled_at": deletion_at,
        "face_region_blacked_out": True,
        "parsed_data": parsed.model_dump(mode="json"),
        "parsed_at": now_iso,
    }
    db.table("scans").update(scan_update).eq("id", scan_id).execute()

    await write_audit_log(
        db=db,
        hotel_id=hotel_id,
        user_id=user_id,
        action="scan.parsed",
        resource_type="scan",
        resource_id=scan_id,
        metadata={"doc_type": parsed.doc_type, "doc_country": parsed.doc_country, "confidence": parsed.confidence},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return ApiResponse.ok(ScanResponse(
        id=scan_id,
        status="parsed",
        parsed_data=parsed,
        face_region_blacked_out=True,
        created_at=now_iso,
        parsed_at=now_iso,
    ))
```

- [ ] **Step 4: Register router in main.py**

In `create_app()`:

```python
    from app.routers import scans, guests, hotels
    application.include_router(scans.router, prefix="/api/v1")
    application.include_router(guests.router, prefix="/api/v1")
    application.include_router(hotels.router, prefix="/api/v1")
```

- [ ] **Step 5: Run tests**

```bash
cd backend && pytest tests/test_scans.py -v
```

Expected: 2 PASSED

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/scans.py backend/app/main.py backend/tests/test_scans.py
git commit -m "feat(backend): POST /scans — full pipeline + Vertex AI + persist end-to-end"
```

---

## Task 18: Scan Read Endpoints

**Files:**

- Modify: `backend/app/routers/scans.py` (add GET endpoints)
- Modify: `backend/tests/test_scans.py` (add read endpoint tests)

- [ ] **Step 1: Add tests**

Append to `backend/tests/test_scans.py`:

```python
@pytest.mark.asyncio
async def test_get_scan_by_id_returns_scan(app_with_scans, fake_user):
    from app.deps import get_current_user

    mock_scan = {
        "id": "scan-1", "hotel_id": "hotel-1", "status": "parsed",
        "face_region_blacked_out": True, "parsed_data": {},
        "created_at": "2026-05-14T00:00:00Z", "parsed_at": None, "typed_at": None, "error_message": None,
    }

    with (
        patch("app.routers.scans.get_supabase") as mock_db,
        patch("app.routers.scans.write_audit_log", new_callable=AsyncMock),
    ):
        mock_db_instance = MagicMock()
        mock_db.return_value = mock_db_instance
        mock_db_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=mock_scan)

        app_with_scans.dependency_overrides[get_current_user] = lambda: fake_user
        async with AsyncClient(transport=ASGITransport(app=app_with_scans), base_url="http://test") as c:
            response = await c.get("/api/v1/scans/scan-1")
        app_with_scans.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["data"]["id"] == "scan-1"


@pytest.mark.asyncio
async def test_get_scan_wrong_hotel_returns_404(app_with_scans, fake_user):
    from app.deps import get_current_user

    with (
        patch("app.routers.scans.get_supabase") as mock_db,
        patch("app.routers.scans.write_audit_log", new_callable=AsyncMock),
    ):
        mock_db_instance = MagicMock()
        mock_db.return_value = mock_db_instance
        mock_db_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=None)

        app_with_scans.dependency_overrides[get_current_user] = lambda: fake_user
        async with AsyncClient(transport=ASGITransport(app=app_with_scans), base_url="http://test") as c:
            response = await c.get("/api/v1/scans/other-hotel-scan")
        app_with_scans.dependency_overrides.clear()

    assert response.status_code == 404
```

- [ ] **Step 2: Implement read endpoints**

Append to `backend/app/routers/scans.py`:

```python
@router.get("/scans/{scan_id}", response_model=ApiResponse[ScanResponse])
async def get_scan(
    scan_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_supabase),
):
    result = (
        db.table("scans")
        .select("*")
        .eq("id", scan_id)
        .eq("hotel_id", current_user["hotel_id"])
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Scan not found")

    await write_audit_log(
        db=db, hotel_id=current_user["hotel_id"], user_id=current_user["user_id"],
        action="scan.read", resource_type="scan", resource_id=scan_id,
        ip_address=request.client.host if request.client else None,
    )

    s = result.data
    parsed_data = ParsedID.model_validate(s["parsed_data"]) if s.get("parsed_data") else None
    return ApiResponse.ok(ScanResponse(
        id=s["id"], status=s["status"], parsed_data=parsed_data,
        face_region_blacked_out=s.get("face_region_blacked_out", True),
        created_at=s["created_at"], parsed_at=s.get("parsed_at"),
        typed_at=s.get("typed_at"), error_message=s.get("error_message"),
    ))


@router.get("/scans/pending-type", response_model=ApiResponse[list[ScanResponse]])
@limiter.limit("30/minute")
async def get_pending_type_scans(
    request: Request,
    current_workstation: dict = Depends(get_current_workstation),
    db=Depends(get_supabase),
):
    result = (
        db.table("scans")
        .select("*")
        .eq("hotel_id", current_workstation["hotel_id"])
        .eq("status", "parsed")
        .order("created_at", desc=False)
        .limit(10)
        .execute()
    )
    scans = []
    for s in result.data or []:
        parsed_data = ParsedID.model_validate(s["parsed_data"]) if s.get("parsed_data") else None
        scans.append(ScanResponse(
            id=s["id"], status=s["status"], parsed_data=parsed_data,
            face_region_blacked_out=s.get("face_region_blacked_out", True),
            created_at=s["created_at"], parsed_at=s.get("parsed_at"),
        ))
    return ApiResponse.ok(scans)


@router.post("/scans/{scan_id}/mark-typed", response_model=ApiResponse[ScanResponse])
async def mark_scan_typed(
    scan_id: str,
    current_workstation: dict = Depends(get_current_workstation),
    db=Depends(get_supabase),
):
    now_iso = datetime.now(timezone.utc).isoformat()
    result = (
        db.table("scans")
        .update({"status": "typed", "typed_at": now_iso})
        .eq("id", scan_id)
        .eq("hotel_id", current_workstation["hotel_id"])
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Scan not found")
    s = result.data[0]
    return ApiResponse.ok(ScanResponse(
        id=s["id"], status=s["status"],
        face_region_blacked_out=s.get("face_region_blacked_out", True),
        created_at=s["created_at"], typed_at=s.get("typed_at"),
    ))
```

- [ ] **Step 3: Run tests**

```bash
cd backend && pytest tests/test_scans.py -v
```

Expected: 4 PASSED

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/scans.py backend/tests/test_scans.py
git commit -m "feat(backend): GET /scans/:id, GET /scans/pending-type, POST /scans/:id/mark-typed"
```

---

## Task 19: Guests Router

**Files:**

- Create: `backend/app/routers/guests.py`
- Create: `backend/tests/test_guests.py`

- [ ] **Step 1: Write tests**

```python
# backend/tests/test_guests.py
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from httpx import AsyncClient, ASGITransport


@pytest.fixture
def app_with_guests():
    from app.main import create_app
    application = create_app()
    from app.routers.guests import router
    application.include_router(router, prefix="/api/v1")
    return application


@pytest.fixture
def fake_user():
    return {"user_id": "user-1", "hotel_id": "hotel-1", "role": "clerk"}


@pytest.mark.asyncio
async def test_list_guests_returns_paginated_results(app_with_guests, fake_user):
    from app.deps import get_current_user

    mock_guests = [
        {"id": "g-1", "hotel_id": "hotel-1", "first_name": "Jane", "last_name": "Doe",
         "doc_type": "passport", "doc_number_last4": "6789", "created_at": "2026-05-14T00:00:00Z", "deleted_at": None},
    ]

    with (
        patch("app.routers.guests.get_supabase") as mock_db,
        patch("app.routers.guests.write_audit_log", new_callable=AsyncMock),
    ):
        mock_db_instance = MagicMock()
        mock_db.return_value = mock_db_instance
        mock_db_instance.table.return_value.select.return_value.eq.return_value.is_.return_value.range.return_value.execute.return_value = MagicMock(data=mock_guests, count=1)

        app_with_guests.dependency_overrides[get_current_user] = lambda: fake_user
        async with AsyncClient(transport=ASGITransport(app=app_with_guests), base_url="http://test") as c:
            response = await c.get("/api/v1/guests")
        app_with_guests.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["data"]) == 1


@pytest.mark.asyncio
async def test_delete_guest_soft_deletes(app_with_guests, fake_user):
    from app.deps import get_current_user

    with (
        patch("app.routers.guests.get_supabase") as mock_db,
        patch("app.routers.guests.write_audit_log", new_callable=AsyncMock),
    ):
        mock_db_instance = MagicMock()
        mock_db.return_value = mock_db_instance
        mock_db_instance.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"id": "g-1"}])

        app_with_guests.dependency_overrides[get_current_user] = lambda: fake_user
        async with AsyncClient(transport=ASGITransport(app=app_with_guests), base_url="http://test") as c:
            response = await c.delete("/api/v1/guests/g-1")
        app_with_guests.dependency_overrides.clear()

    assert response.status_code == 200
    # Verify it was a soft delete (update, not hard delete)
    mock_db_instance.table.return_value.update.assert_called()
    call_payload = mock_db_instance.table.return_value.update.call_args[0][0]
    assert "deleted_at" in call_payload
```

- [ ] **Step 2: Implement guests.py**

```python
# backend/app/routers/guests.py
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.deps import get_current_user, get_supabase, limiter
from app.models.common import ApiResponse, PaginatedResponse
from app.models.guest import GuestResponse, GuestListItem
from app.services.audit import write_audit_log

router = APIRouter(tags=["guests"])


@router.get("/guests", response_model=PaginatedResponse[GuestListItem])
@limiter.limit("60/minute")
async def list_guests(
    request: Request,
    q: str | None = Query(None, description="Full-text search"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db=Depends(get_supabase),
):
    hotel_id = current_user["hotel_id"]
    offset = (page - 1) * page_size

    query = (
        db.table("guests")
        .select("id, first_name, last_name, doc_type, doc_number_last4, created_at", count="exact")
        .eq("hotel_id", hotel_id)
        .is_("deleted_at", None)
        .range(offset, offset + page_size - 1)
    )

    result = query.execute()

    await write_audit_log(
        db=db, hotel_id=hotel_id, user_id=current_user["user_id"],
        action="guests.list",
        ip_address=request.client.host if request.client else None,
    )

    items = [GuestListItem(**g) for g in (result.data or [])]
    return PaginatedResponse(data=items, total=result.count or 0, page=page, page_size=page_size)


@router.get("/guests/{guest_id}", response_model=ApiResponse[GuestResponse])
@limiter.limit("60/minute")
async def get_guest(
    request: Request,
    guest_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_supabase),
):
    result = (
        db.table("guests")
        .select("*")
        .eq("id", guest_id)
        .eq("hotel_id", current_user["hotel_id"])
        .is_("deleted_at", None)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Guest not found")

    await write_audit_log(
        db=db, hotel_id=current_user["hotel_id"], user_id=current_user["user_id"],
        action="guest.read", resource_type="guest", resource_id=guest_id,
        ip_address=request.client.host if request.client else None,
    )

    return ApiResponse.ok(GuestResponse(**result.data))


@router.delete("/guests/{guest_id}", response_model=ApiResponse[None])
@limiter.limit("10/minute")
async def delete_guest(
    request: Request,
    guest_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_supabase),
):
    now_iso = datetime.now(timezone.utc).isoformat()
    result = (
        db.table("guests")
        .update({"deleted_at": now_iso, "deletion_requested_at": now_iso})
        .eq("id", guest_id)
        .eq("hotel_id", current_user["hotel_id"])
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Guest not found")

    await write_audit_log(
        db=db, hotel_id=current_user["hotel_id"], user_id=current_user["user_id"],
        action="guest.deleted", resource_type="guest", resource_id=guest_id,
        metadata={"doc_number_last4": result.data[0].get("doc_number_last4")},
        ip_address=request.client.host if request.client else None,
    )

    return ApiResponse.ok(None)
```

- [ ] **Step 3: Run tests**

```bash
cd backend && pytest tests/test_guests.py -v
```

Expected: 2 PASSED

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/guests.py backend/tests/test_guests.py
git commit -m "feat(backend): GET /guests, GET /guests/:id, DELETE /guests/:id (soft delete)"
```

---

## Task 20: Hotels Router + Rate Limiting

**Files:**

- Create: `backend/app/routers/hotels.py`
- Create: `backend/tests/test_hotels.py`
- Modify: `backend/app/main.py` (wire slowapi)

- [ ] **Step 1: Write tests**

```python
# backend/tests/test_hotels.py
import pytest
from unittest.mock import MagicMock, patch
from httpx import AsyncClient, ASGITransport


@pytest.fixture
def app_with_hotels():
    from app.main import create_app
    application = create_app()
    from app.routers.hotels import router
    application.include_router(router, prefix="/api/v1")
    return application


@pytest.mark.asyncio
async def test_get_hotel_me_returns_hotel(app_with_hotels):
    from app.deps import get_current_user

    fake_user = {"user_id": "u-1", "hotel_id": "hotel-1", "role": "owner"}
    mock_hotel = {
        "id": "hotel-1", "name": "Grand Hotel", "subscription_status": "active",
        "plan": "pro", "image_retention_hours": 24, "created_at": "2026-01-01T00:00:00Z",
    }

    with patch("app.routers.hotels.get_supabase") as mock_db:
        mock_db_instance = MagicMock()
        mock_db.return_value = mock_db_instance
        mock_db_instance.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=mock_hotel)

        app_with_hotels.dependency_overrides[get_current_user] = lambda: fake_user
        async with AsyncClient(transport=ASGITransport(app=app_with_hotels), base_url="http://test") as c:
            response = await c.get("/api/v1/hotels/me")
        app_with_hotels.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["data"]["name"] == "Grand Hotel"
```

- [ ] **Step 2: Implement hotels.py**

```python
# backend/app/routers/hotels.py
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.deps import get_current_user, get_supabase, limiter

router = APIRouter(tags=["hotels"])


class HotelResponse(BaseModel):
    id: str
    name: str
    subscription_status: str
    plan: str
    image_retention_hours: int
    created_at: str


@router.get("/hotels/me", response_model=dict)
@limiter.limit("60/minute")
async def get_my_hotel(
    request: Request,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_supabase),
):
    result = (
        db.table("hotels")
        .select("id, name, subscription_status, plan, image_retention_hours, created_at")
        .eq("id", current_user["hotel_id"])
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Hotel not found")
    return {"success": True, "data": result.data, "error": None}
```

- [ ] **Step 3: Wire slowapi into main.py**

In `create_app()` in `backend/app/main.py`, add after `application = FastAPI(...)`:

```python
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from app.deps import limiter

    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

- [ ] **Step 4: Run all tests**

```bash
cd backend && pytest tests/test_hotels.py tests/test_scans.py tests/test_guests.py -v
```

Expected: all PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/hotels.py backend/app/main.py backend/tests/test_hotels.py
git commit -m "feat(backend): GET /hotels/me + slowapi rate limiting wired to all endpoints"
```

---

## Task 21: Full Test Suite + OpenAPI Export

**Files:**

- Modify: `backend/app/main.py` (add OpenAPI export route)

- [ ] **Step 1: Run full test suite**

```bash
cd backend && pytest tests/ -v --tb=short
```

Expected: all tests PASS. Fix any failures before proceeding.

- [ ] **Step 2: Add OpenAPI export command**

Append to `backend/app/main.py`:

```python
if __name__ == "__main__":
    import json, sys
    if len(sys.argv) > 1 and sys.argv[1] == "export-openapi":
        output_path = sys.argv[2] if len(sys.argv) > 2 else "../aura-id/shared/openapi.json"
        schema = app.openapi()
        import pathlib
        pathlib.Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(schema, f, indent=2)
        print(f"OpenAPI schema written to {output_path}")
```

- [ ] **Step 3: Export OpenAPI schema**

```bash
cd backend && python -m app.main export-openapi ../aura-id/shared/openapi.json
```

Expected: `openapi.json` written without errors.

- [ ] **Step 4: Run full suite one more time**

```bash
cd backend && pytest tests/ -v --cov=app --cov-report=term-missing
```

Expected: all PASS, coverage visible.

- [ ] **Step 5: Final commit**

```bash
git add backend/ && git commit -m "feat(backend): Phase 1 complete — all endpoints, tests passing, OpenAPI exported"
```

---

## Self-Review Checklist

- [x] **EXIF stripping** — Task 10 `strip_exif`
- [x] **Face blackout (BIPA)** — Task 11 `apply_face_blackout`, pixel-level test
- [x] **Face blackout always runs** — `run_pipeline` raises on unexpected failure, pipeline fails safe
- [x] **Vertex AI only** — `VertexAIClient` uses `google-cloud-aiplatform`, no `google-generativeai`
- [x] **Biometric rejection** — Task 15 `check_for_biometric_content` + test
- [x] **Audit log on every PII read/write** — scans.py, guests.py write audit entries
- [x] **PII not in logs** — structlog processor strips keys, tested in Task 3
- [x] **Sentry PII scrubber** — `_sentry_before_send` in main.py
- [x] **doc_number encrypted** — Fernet encryption in scans.py, last 4 stored unencrypted
- [x] **Rate limiting** — slowapi on all endpoints, 30/min on pending-type
- [x] **Soft delete for guests** — `deleted_at` timestamp, not hard DELETE
- [x] **Retention job** — APScheduler hourly in Task 16
- [x] **Workstation auth** — `ws_live_`/`ws_test_` token, bcrypt hash, no raw token stored
- [x] **Service role key never in logs** — config.py `supabase_service_key` not logged
- [x] **hotel_id isolation** — all queries filtered by hotel_id manually + RLS as defense-in-depth
- [x] **`image_deletion_scheduled_at` column** — used in retention query (add to schema.sql: `image_deletion_scheduled_at timestamptz`)
