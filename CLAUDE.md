# Project: Aura ID — Desktop Agent + Web Platform

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

## What Was Built

### Aura Desktop Agent (`agent/` branch: `agent`)

Full Python 3.11 Windows desktop agent. Hotel clerks press Ctrl+Shift+A and the agent types ID scan data from the Aura ID backend directly into the focused PMS window.

**Modules:**
- `agent/src/config.py` — Pydantic settings (`AURA_*` env prefix, keyring token)
- `agent/src/models.py` — `ScanData` dataclass (in-memory only, never serialised)
- `agent/src/pii_guard.py` — `wipe(ScanData)` zeroes all PII fields + `gc.collect()`
- `agent/src/utils/logging.py` — structlog processor that drops any event containing PII keys or email patterns
- `agent/src/pairing.py` — `PairingClient` (POST `/workstations/claim`), tkinter pairing dialog, keyring token helpers
- `agent/src/pms_profiles/loader.py` — `ProfileLoader` loads 5 JSON PMS profiles (opera, synxis, cloudbeds, hotelkey, generic); `match_window()` matches active window title by regex
- `agent/src/utils/window_detect.py` — Win32 ctypes active window title
- `agent/src/poller.py` — background poll loop (`GET /scans/pending-type`), `mark_typed()` audit POST
- `agent/src/typer.py` — `TyperEngine.type_scan()`: PyAutoGUI typing, DOB reformatting, 10s hard cap
- `agent/src/tray.py` — pystray system tray with 5 states (idle/waiting/typing/error/subscription_inactive)
- `agent/src/sentry_setup.py` — `scrub_sentry_event` before_send hook strips PII from extra/tags/frame vars; redacts emails in-place
- `agent/src/updater.py` — semver comparison against `updates.auraid.com/latest.json`; validates download URL origin
- `agent/src/main.py` — `AgentApp` orchestrator + `SubscriptionChecker`; `wipe()` called in `finally` on every hotkey path

**Build:**
- `agent/aura_agent.spec` — PyInstaller single-exe spec
- `agent/installer/aura-agent.iss` — Inno Setup; admin install, startup task, uninstall wipes keyring + AppData
- `agent/installer/sign.bat` — EV code-signing (SHA-256 + RFC 3161 timestamp)
- `agent/build.bat` — PyInstaller → Inno Setup → sign pipeline

**Tests:** 59 passing across 11 test modules. Run with: `cd agent && python -m pytest`

**Compliance posture:**
- Zero PII ever written to disk
- `pii_guard.wipe()` always called after typing (enforced by `finally` block)
- Structlog processor drops events containing PII keys or email patterns
- Sentry `before_send` scrubs PII from all event sections
- Workstation token stored in Windows Credential Manager (keyring) only
- HTTPS only, TLS verification always on

---

## Stack & Conventions

### Desktop Agent (Python)
- Runtime: Python 3.11
- Test: `cd agent && python -m pytest`
- Lint: `cd agent && python -m ruff check src tests`
- Format: `cd agent && python -m black src tests`
- Import style: `from src.xxx import` (packages=["src"] in hatchling — intentional)
- Commit format: `feat/fix/chore(scope): description`

### Web Platform (Next.js — repo root)
- Runtime: Node.js with npm
- Build: `npm run build`
- Typecheck: `npm run typecheck`
- Tests: `npm test`
- Single file: `npm test -- --testPathPattern="<glob>"`

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
