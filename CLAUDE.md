# Project: my-project

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
