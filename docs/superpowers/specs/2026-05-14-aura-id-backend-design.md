# Aura ID Backend — Phase 1 Design Spec

**Date:** 2026-05-14
**Scope:** Phase 1 — Foundation + image pipeline + core scan/guest endpoints
**Status:** Approved

---

## 1. Context

Aura ID is a B2B SaaS that captures guest IDs at hotels via mobile, extracts text-only data using Google Vertex AI (Gemini 2.5 Flash), and feeds it to a desktop typing agent that auto-fills legacy hotel PMS software.

**Compliance posture (non-negotiable):**

- No biometric processing. Face region is blacked out before any image leaves the pipeline.
- Vertex AI only (no direct Gemini API). Google's contractual DPA and no-training guarantee apply.
- Images auto-delete within 24h by default (max 30 days configurable per hotel).
- Append-only audit log on every PII read/write, retained 7 years.
- No PII in logs (names masked, DOB omitted, doc numbers last-4 only).
- EXIF stripped on every upload.

---

## 2. Repository Layout

```
aura-id-backend/
├── backend/                    ← Python project root
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── deps.py
│   │   ├── middleware/
│   │   │   ├── audit.py
│   │   │   ├── pii_scrubber.py
│   │   │   └── subscription_gate.py
│   │   ├── routers/
│   │   │   ├── scans.py
│   │   │   ├── guests.py
│   │   │   ├── users.py
│   │   │   ├── hotels.py
│   │   │   ├── workstations.py
│   │   │   ├── billing.py
│   │   │   ├── webhooks.py
│   │   │   └── data_subject.py
│   │   ├── services/
│   │   │   ├── image_pipeline.py
│   │   │   ├── vertex_ai.py
│   │   │   ├── stripe_service.py
│   │   │   ├── storage.py
│   │   │   ├── audit.py
│   │   │   └── retention.py
│   │   ├── models/
│   │   └── db/
│   │       ├── schema.sql
│   │       └── migrations/
│   ├── tests/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── .env.example
│   └── README.md
└── docs/
```

---

## 3. Stack

| Layer               | Technology                                                                               |
| ------------------- | ---------------------------------------------------------------------------------------- |
| Runtime             | Python 3.11, FastAPI, async                                                              |
| Auth (humans)       | Supabase Auth — JWT decoded in `deps.py`                                                 |
| Auth (workstations) | Opaque `ws_live_` token, bcrypt-hashed in DB                                             |
| Database            | Supabase Postgres, RLS on all tenant tables                                              |
| Storage             | Supabase Storage, private bucket, signed URLs                                            |
| AI                  | Vertex AI Python SDK, Gemini 2.5 Flash, structured output                                |
| Image processing    | Pillow + piexif (EXIF strip), MediaPipe Face Detection (CPU, face blackout only), OpenCV |
| Background jobs     | APScheduler (in-process, hourly retention sweep)                                         |
| Logging             | structlog with PII-scrubbing processor                                                   |
| Error tracking      | Sentry SDK with `before_send` PII scrubber                                               |
| Encryption          | pgcrypto for `doc_number` at rest                                                        |
| Rate limiting       | slowapi (Starlette middleware)                                                           |
| Testing             | pytest + httpx                                                                           |
| Deploy              | Railway, Dockerfile (multi-stage, non-root user)                                         |

---

## 4. Database Schema

All tenant tables include `hotel_id` with RLS:

```sql
USING (hotel_id = (auth.jwt() ->> 'hotel_id')::uuid)
```

### hotels

```sql
hotels(id uuid pk, name, address, stripe_customer_id, subscription_status,
       plan, image_retention_hours int default 24, dpa_signed_at, dpa_version,
       created_at, updated_at)
```

### users

```sql
users(id uuid pk, hotel_id uuid fk, email, role enum[owner|clerk],
      consent_given_at, created_at, last_login_at)
```

### guests

```sql
guests(id uuid pk, hotel_id uuid fk, first_name, last_name, dob,
       doc_number_last4, doc_number_encrypted bytea,  -- pgcrypto
       doc_type, doc_country, email, phone, address, nationality, notes,
       search_vector tsvector, deletion_requested_at, deleted_at,
       created_at, updated_at)
```

### scans

```sql
scans(id uuid pk, hotel_id uuid fk, guest_id uuid nullable,
      user_id uuid fk, workstation_id uuid nullable,
      image_path text nullable,
      image_deleted_at timestamptz,
      status enum[pending|parsed|typed|failed|expired],
      parsed_data jsonb,
      face_region_blacked_out bool default true,  -- compliance flag
      error_message, created_at, parsed_at, typed_at)
```

### workstations

```sql
workstations(id uuid pk, hotel_id uuid fk, name,
             pairing_code text, pairing_code_expires_at,
             token_hash text,      -- bcrypt hash, never raw
             token_prefix text,    -- first 12 chars for display
             revoked_at timestamptz,
             last_used_at timestamptz,
             paired_at, last_seen_at)
```

### audit_log

```sql
audit_log(id uuid pk, hotel_id uuid, user_id uuid nullable,
          action, resource_type, resource_id, metadata jsonb,
          ip_address, user_agent, created_at)
-- INDEX (hotel_id, created_at DESC)
-- Retained 7 years. No DELETE permission except quarterly archive.
```

### data_subject_requests

```sql
data_subject_requests(id uuid pk, hotel_id uuid, requester_email,
                      request_type enum[access|delete|export],
                      status, completed_at, created_at)
```

---

## 5. Image Pipeline (9 Steps)

The most compliance-critical code. Every step runs synchronously within the scan upload request. If any step fails, the scan is rejected with `status=failed` — there is no partial-success path.

| Step | Action                                                        | Compliance note                            |
| ---- | ------------------------------------------------------------- | ------------------------------------------ |
| 1    | Validate: max 8MB, JPEG/PNG/HEIC only, MIME matches extension |                                            |
| 2    | Strip EXIF via piexif + re-encode through Pillow              | Removes GPS, device ID                     |
| 3    | Detect face via MediaPipe Face Detection (CPU)                | Detection only — no embeddings extracted   |
| 4    | **Blackout face** — solid black rect, bbox + 10% padding      | **Critical BIPA step**                     |
| 5    | Compress: max 1600px longest edge, JPEG q85                   |                                            |
| 6    | Upload blacked-out image to Supabase Storage                  | Deletion timestamp = now + retention_hours |
| 7    | Send to Vertex AI (structured output, `ParsedID` schema)      | Vertex AI only — no direct Gemini API      |
| 8    | Persist: scans + guests upsert, encrypt doc_number            |                                            |
| 9    | (Background) Hourly job deletes images past retention         |                                            |

**Face-blackout failure modes:**

- No face detected → proceed, log warning, `face_region_blacked_out=true` still set (no face = nothing to blackout)
- Multiple faces → blackout ALL bounding boxes
- MediaPipe crashes → scan fails, return 422

**Vertex AI biometric rejection:** If the response text contains eye color, facial features, or physical descriptors, reject the response, log to Sentry, set `status=failed`.

---

## 6. Auth Design

### Human clerks (Supabase JWT)

- `Authorization: Bearer <supabase_jwt>`
- `get_current_user` dependency decodes JWT, extracts `hotel_id` claim
- Used by: all `/guests`, `/scans` (upload), `/hotels/me`, `/users`

### Workstations (opaque token)

- `Authorization: Bearer ws_live_<32-char-urlsafe-base64>`
- `ws_test_` prefix in non-production
- `get_current_workstation` dependency: hash token → lookup → check revoked → debounce `last_used_at`
- Used by: `GET /scans/pending-type`, `POST /scans/:id/mark-typed`, `GET /hotels/me` (agent view), `POST /workstations/heartbeat`

---

## 7. Phase 1 API Endpoints

| Method | Path                           | Auth                     | Rate limit                                |
| ------ | ------------------------------ | ------------------------ | ----------------------------------------- |
| POST   | `/api/v1/scans`                | clerk JWT                | 30/min per workstation, 100/min per hotel |
| GET    | `/api/v1/scans/:id`            | clerk JWT                | 60/min per hotel                          |
| GET    | `/api/v1/scans/pending-type`   | workstation token        | 30/min per token                          |
| POST   | `/api/v1/scans/:id/mark-typed` | workstation token        | 60/min per token                          |
| GET    | `/api/v1/guests`               | clerk JWT                | 60/min per hotel                          |
| GET    | `/api/v1/guests/:id`           | clerk JWT                | 60/min per hotel                          |
| DELETE | `/api/v1/guests/:id`           | clerk JWT                | 10/min per hotel                          |
| GET    | `/api/v1/hotels/me`            | clerk JWT or workstation | 60/min                                    |
| GET    | `/health`                      | none                     | none                                      |

All responses: `{"success": bool, "data": ..., "error": str | null}`

---

## 8. Logging & PII Rules

- structlog with a `pii_scrub_processor` that runs on every log line
- Names → first initial + last name (`J. Smith`)
- DOB → omitted entirely from logs
- Doc numbers → last 4 only
- Sentry `before_send` hook strips all PII fields
- Service-role Supabase key never logged

---

## 9. Testing Strategy

- Unit tests per pipeline step, including pixel-level blackout verification
- `FakeVertexClient` implementing `AbstractVertexClient` for AI tests
- `httpx.AsyncClient` with `app` transport for endpoint integration tests
- PII scrubber tested by injecting a known-PII log record and asserting output is masked

---

## 10. Open Decisions (Resolved)

| Decision                 | Chosen                      | Rationale                                            |
| ------------------------ | --------------------------- | ---------------------------------------------------- |
| `doc_number` encryption  | pgcrypto                    | No extra service; works in any Postgres              |
| Background retention     | APScheduler in-process      | Railway single-container; zero extra infra           |
| Vertex AI test isolation | Stub class behind interface | Stable CI, no network dependency                     |
| Workstation auth         | Pre-shared opaque token     | Simple, revocable, no JWT rotation complexity for v1 |
| Repo layout              | `backend/` subdirectory     | Clean separation; Next.js template files removed     |
| Build scope              | Phase 1 only                | Ship working core before billing/GDPR phases         |
