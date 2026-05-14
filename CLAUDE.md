# Project: my-project

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

## Stack & Conventions

- Runtime: Node.js with npm
- JavaScript (keep strict, no unnecessary defaults)
- Commit format: feat/fix/chore(scope): description

## Commands

- Build: npm run build
- Typecheck (fast): npm run typecheck
- Tests: npm test
- Single file: npm test -- --testPathPattern="<glob>"

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
