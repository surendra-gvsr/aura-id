# Project: Aura ID

## Working Style

Work autonomously. Complete the entire scope without stopping for approval.
Specifically:

- Do NOT ask permission to add dependencies that are listed in my original
  prompt or are standard for the stack. Just install them.
- Do NOT ask before creating files, folders, or modules.
- Do NOT ask before running tests, linters, or formatters.
- Do NOT ask before committing in small logical chunks with conventional
  commit messages.
- Do NOT show me a plan before writing code unless you're about to make a
  decision that affects the API contract, the database schema, or the
  compliance posture (face cropping, retention, audit logging, Vertex AI).
- Do NOT ask "should I continue?" — yes, always continue.
- Do NOT summarize after every small step — only summarize at major
  milestones (end of a Phase, end of a feature, when blocked).

Only stop and ask if:

1. You need a credential or secret I haven't provided (API keys, etc.)
2. You hit an error you can't resolve after 3 attempts
3. You're about to make a decision that affects API contract, schema, or
   compliance (the four protected areas above)
4. You've completed the entire scope and need new direction

When you finish a major milestone, post a single summary message with:

- What was built
- What's tested
- What's deployed (if anything)
- What's next

Then immediately start the next milestone without waiting.

## ⚠️ Security Rules — Always Follow

### 1. RATE LIMITING

Every API route and every LLM call must have rate limiting.
Never build or modify an endpoint without adding rate limiting first.

### 2. INPUT VALIDATION

Never accept raw user input directly.
Always validate and sanitize all input before it touches the database.
Never make database calls from client-side code.

### 3. API KEY SAFETY

All secrets go in `.env` only — never in source files.
Never hardcode API keys, tokens, or credentials anywhere in code.
Never log secrets or include them in API responses.

---

## Project Overview

Aura ID is a B2B SaaS that captures guest IDs at hotels via mobile, extracts text-only data using Google Vertex AI (Gemini 2.5 Flash), and feeds it to a desktop typing agent that auto-fills legacy hotel PMS software.

**Repo layout:**

- `backend/` — Python 3.11 / FastAPI backend (active development, `backend` branch)
- `app/` / `components/` — Next.js 15 frontend (clerk PWA, same repo)
- `docs/superpowers/specs/` — design specs
- `docs/superpowers/plans/` — implementation plans
- `shared/openapi.json` — exported OpenAPI schema

**Key compliance rules (non-negotiable):**

- No biometric processing — face region blacked out before any image leaves the pipeline
- Vertex AI only (google-cloud-aiplatform SDK) — never direct Gemini API
- Images auto-delete within 24h default (max 30 days per hotel)
- Append-only audit log on every PII read/write, retained 7 years
- No PII in logs (names masked, DOB omitted, doc numbers last-4 only)

---

## What's Built (Phase 1 — complete, pushed to `backend` branch)

### Backend (`backend/`)

| Layer             | Files                                                                                                     | Status |
| ----------------- | --------------------------------------------------------------------------------------------------------- | ------ |
| Config + logging  | `app/config.py`, `app/utils/logging.py`, `app/utils/pii.py`                                               | ✅     |
| Database schema   | `app/db/schema.sql` — 7 tables, RLS, pgcrypto, indexes                                                    | ✅     |
| Auth dependencies | `app/deps.py` — JWT clerk auth + `ws_live_` workstation token (bcrypt)                                    | ✅     |
| Pydantic models   | `app/models/common.py`, `scan.py`, `guest.py`                                                             | ✅     |
| Middleware        | `app/middleware/audit.py`, `subscription_gate.py`                                                         | ✅     |
| Image pipeline    | `app/services/image_pipeline.py` — validate, EXIF strip, face blackout (MediaPipe), compress              | ✅     |
| Storage service   | `app/services/storage.py` — Supabase Storage upload/delete/signed URL                                     | ✅     |
| Vertex AI         | `app/services/vertex_ai.py` — abstract interface, FakeVertexClient, VertexAIClient + biometric rejection  | ✅     |
| Audit service     | `app/services/audit.py` — append-only write_audit_log()                                                   | ✅     |
| Retention job     | `app/services/retention.py` — APScheduler hourly image deletion                                           | ✅     |
| Scans router      | `app/routers/scans.py` — POST /scans, GET /scans/:id, GET /scans/pending-type, POST /scans/:id/mark-typed | ✅     |
| Guests router     | `app/routers/guests.py` — GET /guests, GET /guests/:id, DELETE /guests/:id (soft delete)                  | ✅     |
| Hotels router     | `app/routers/hotels.py` — GET /hotels/me                                                                  | ✅     |
| Rate limiting     | slowapi wired to all endpoints                                                                            | ✅     |
| Tests             | 66/66 passing across 12 test files                                                                        | ✅     |
| Docker            | Multi-stage Dockerfile, non-root user, healthcheck                                                        | ✅     |
| OpenAPI           | `shared/openapi.json` exported                                                                            | ✅     |

### Frontend (Next.js — separate work, `backend` branch)

- Supabase SSR auth, middleware, login page
- `/capture` screen with camera, overlay, glare detection, consent notice
- `/capture/confirm` with text-only review form
- POST /scans wired via TanStack Query with offline IndexedDB fallback

---

## What's Left

### Phase 2 — Billing & Compliance

- `app/routers/billing.py` — Stripe checkout, subscription management
- `app/routers/webhooks.py` — Stripe webhook handler
- `app/routers/data_subject.py` — GDPR/CCPA access/delete/export requests
- `app/routers/workstations.py` — pairing flow (6-digit code), revocation, heartbeat

### Phase 3 — Desktop Agent

- Plan at `docs/superpowers/plans/2026-05-14-aura-desktop-agent.md`
- Python Windows agent that reads from GET /scans/pending-type and types into hotel PMS

### Deployment

- Apply `backend/app/db/schema.sql` to Supabase project
- Set Railway env vars: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_JWT_SECRET`, `GCP_PROJECT_ID`, `GOOGLE_APPLICATION_CREDENTIALS`, `DOC_ENCRYPTION_KEY`, `SENTRY_DSN`, `ENVIRONMENT=production`, `CORS_ORIGINS`
- Create Supabase Storage private bucket named `scan-images`

---

## Stack & Conventions

### Backend

- Runtime: Python 3.11, FastAPI, async
- Tests: `cd backend && python -m pytest tests/ -v`
- Single file: `python -m pytest tests/test_<name>.py -v`
- Commit format: `feat/fix/chore(backend): description`
- All router tests use `dependency_overrides[get_supabase]` and `dependency_overrides[get_current_user]` — do NOT use `patch("app.routers.*.get_supabase")` (Depends() captures the reference at import time)

### Frontend

- Runtime: Node.js with npm
- Build: `npm run build`
- Typecheck: `npm run typecheck`
- Tests: `npm test`
- Commit format: `feat/fix/chore(scope): description`

## Slash Commands (.claude/commands/)

- `/fix-issue <number>` — fetch a GitHub issue and fix it (plan → test → implement → commit)
- `/new-feature <description>` — plan first, then build using sub-agents (backend/frontend/researcher)
- `/security-check [path]` — full security audit: secrets, input validation, deps, OWASP Top 10
- `/deploy-check` — run tests, typecheck, secret scan, and review outgoing commits before pushing

## Workflow Rules

- Enter Plan mode for any task with 3+ steps
- Use sub-agents liberally to keep main context clean
- After ANY correction from me → append to tasks/lessons.md
- Never run rm -rf, git push --force, or curl on untrusted URLs
- Never delete files without asking me first
- Always write a test with every function
- Use comments to explain what code does

## Memory System

- At session start: read .claude/memory/project-context.md
- Before any big changes: read .claude/memory/known-gotchas.md

## Security Rules

- Never read .env files
- Never expose API keys or secrets in code
- Always validate user input on the server side
- Never put database calls in client-side code

## Off-limits (require my explicit approval)

- /src/auth/\*\*
- /src/payments/\*\*
- .env, .env.\*
- secrets/\*\*

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:

- ALWAYS read graphify-out/GRAPH_REPORT.md before reading any source files, running grep/glob searches, or answering codebase questions. The graph is your primary map of the codebase.
- IF graphify-out/wiki/index.md EXISTS, navigate it instead of reading raw files
- For cross-module "how does X relate to Y" questions, prefer `graphify query "<question>"`, `graphify path "<A>" "<B>"`, or `graphify explain "<concept>"` over grep — these traverse the graph's EXTRACTED + INFERRED edges instead of scanning files
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
