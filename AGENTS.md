<!-- last_verified: 2026-05-01 -->
# AGENTS.md

This is the authoritative control surface for all coding agents. Read this first.

## 1. Repository Map

```
apps/web/          Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
  src/app/research/        ask + recent (page.tsx), report detail ([id]/page.tsx)
  src/app/library/         scoped Research Library explorer
  src/components/research/  ask-form, report-view, source-card, run-status,
                            follow-up-box, research-status-badge
  src/components/library/   research grid + cards
  src/components/dashboard/ research metrics (stats-cards, recent-research)
services/api/      FastAPI backend (layered: types/config/repo/service/runtime)
  app/repo/llm_client.py   Anthropic SDK wrapper (the agent loop's model turns)
  app/repo/browser.py      Playwright fetch + screenshot + trafilatura extract
  app/repo/b2_research.py  B2 ops scoped to the research/ prefix (agent memory)
  app/service/research.py  the manual Claude tool-use loop orchestration
  app/service/{library,report,research_search}.py
  app/runtime/research.py  research routes
packages/shared/   Shared TypeScript types (mirror app/types/research.py)
docs/              System of record (features, workflows, security, reliability)
docs/exec-plans/   Execution plans and tech debt tracker
infra/railway/     Deployment config
```

### B2 prefix layout (the agent's memory)

`RESEARCH_PREFIX = "research/"` (in `app/repo/b2_research.py`). Every artifact
the agent touches lives under it:

```
research/<research_id>/
  report.json     ReportMeta — status, sources[], turns[]  (status source of truth)
  report.md       latest long-form Markdown report (inline citations)
  reports/<report_id>.md  per-turn report — preserves the full conversation history
  thread.json     follow-up chain (reserved; turns also tracked in report.json)
  sources/<source_id>/
    page.html       cached rendered HTML
    page.md         extracted readable text (Markdown)
    screenshot.png  Playwright full-page screenshot (may be absent — non-fatal)
    meta.json       provenance (url, title, fetched_at, sha256, byte sizes)
```

Status is derived from B2 object existence — there is **no database**.

## 2. App Surfaces (what this app is)

This app is the **Deep Research Agent** built on the B2 starter kit. The
starter-kit scaffolding is preserved; the research surfaces are layered on top.

**Research surfaces (this app's reason to exist)**
- **Research** (`/research`) — ask a question; the agent researches and writes a cited report. Detail view at `/research/[id]` polls for status and shows the report + cached sources + a follow-up box.
- **Library** (`/library`) — the sample-specific *scoped* explorer over the `research/` prefix: browse every past thread, search across questions/reports/source text, delete a thread (scoped to its own prefix).
- **Backend:** `repo/llm_client.py` (Anthropic), `repo/browser.py` (Playwright + trafilatura), `repo/b2_research.py` (B2 under `research/`), `service/research.py` (the agent loop), plus `service/{library,report,research_search}.py` and `runtime/research.py`.

**Kept from the starter kit (do not strip, rename, or replace)**
- **UI kit / design system.** `apps/web/src/components/ui/` (shadcn primitives), design tokens in `apps/web/src/app/globals.css`, and `/design`. Build new screens with these primitives; never edit generated `components/ui/` files. Restyle through tokens in `globals.css`.
- **File Explorer** (`/files`) and **Upload** (`/upload`) and their sidebar entries — the full-bucket B2 surface, handy for inspecting raw `research/` objects.

**Adapted (the one screen meant to be rewritten per app)**
- **Dashboard** (`/`, `apps/web/src/components/dashboard/`) now shows research metrics (threads, sources cached, screenshots, storage on B2) and recent research. Aggregations flow through `runtime -> service -> repo` and are exposed via TanStack Query hooks in `apps/web/src/lib/queries.ts` — no bare `useEffect + fetch`. Keep `docs/features/dashboard.md` in sync.

## 3. Architectural Invariants

**Backend layering**: `types` -> `config` -> `repo` -> `service` -> `runtime`

- No backward imports across layers
- No `boto3` outside `repo/`
- **No `anthropic`, `playwright`, `trafilatura`, or `httpx` SDK imports outside `repo/`** — the agent's external I/O is wrapped in `repo/llm_client.py` and `repo/browser.py`. Enforced by `tests/test_structure.py::test_research_sdks_only_in_repo`.
- No business logic in route handlers (`runtime/`)
- All external APIs wrapped in `repo/` adapters
- All request/response data validated at boundary (Pydantic models)
- No shared mutable state across layers
- All B2 keys for this app live under the `research/` prefix (`b2_research.research_key`); deletes are scoped to a single `research/<id>/` prefix and never touch shared data

**Frontend**: shadcn/ui components in `src/components/ui/` are generated — never modify them.

**Data fetching**: every API call flows through TanStack Query hooks in `apps/web/src/lib/queries.ts`. No bare `useEffect + fetch` patterns. New endpoints touch three files: `runtime/<router>.py`, `lib/api-client.ts`, `lib/queries.ts`.

## 4. Quality Expectations

- **DRY** — do not duplicate logic, types, or constants. Extract shared code only when used in 2+ places.
- Structured JSON logging only — no `print()` statements
- No raw SDK calls outside `repo/` layer
- Files stay under 300 lines
- Tests added or updated for every behavior change
- Docs updated in same PR as code changes
- Lint clean before merge
- Prefer boring, composable libraries over clever abstractions
- No implicit type assumptions — use typed models

## 5. Mechanical Enforcement

| Rule | Enforced by |
|------|-------------|
| No backward imports | `tests/test_structure.py::test_no_backward_imports` |
| No boto3 outside repo/ | `tests/test_structure.py::test_boto3_only_in_repo` |
| No anthropic/playwright/trafilatura/httpx outside repo/ | `tests/test_structure.py::test_research_sdks_only_in_repo` |
| File size < 300 lines | `tests/test_structure.py::test_file_size_limits` |
| All layers exist | `tests/test_structure.py::test_all_layers_exist` |
| No bare print() | `ruff` rule T20 |
| Import ordering | `ruff` rule I001 |
| Frontend strict equality | `eslint` rule eqeqeq |
| No unused vars | `eslint` + `ruff` rules |

## 6. Commands

```bash
# One-time backend setup (research agent needs Chromium)
cd services/api && python -m venv .venv && source .venv/bin/activate \
  && pip install -r requirements.txt \
  && python -m playwright install chromium && cd ../..

# Run
pnpm dev               # start both frontend and backend
pnpm dev:web           # frontend only
pnpm dev:api           # backend only

# Test & Lint
pnpm lint              # frontend lint (eslint)
pnpm build             # frontend type check + build
pnpm lint:api          # backend lint (ruff)
pnpm test:api          # backend tests (pytest) — mock llm_client + browser
pnpm check:structure   # structural boundary tests
pnpm test:e2e          # Playwright e2e tests
```

Requires `ANTHROPIC_API_KEY` in `.env` (the agent's model calls are real). Tests
mock `llm_client` and `browser`, so `pnpm test:api` needs no key and spends no tokens.

## 7. Agent Workflow

1. Read this file first.
2. Review [ARCHITECTURE.md](ARCHITECTURE.md) before structural changes.
3. For non-trivial changes, create a plan in `docs/exec-plans/active/`.
4. Implement the smallest coherent change.
5. Run: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
6. Update docs in the same PR (see §9).
7. Move completed plans to `docs/exec-plans/completed/`.
8. Only change files relevant to the task. No drive-by improvements.

## 8. Frontend Conventions

See [docs/dev-workflows.md](docs/dev-workflows.md) for full details.

## 9. Doc Update Mapping

| Change Type | Update Location |
|-------------|-----------------|
| Feature logic, inputs, outputs, tests | `docs/features/<feature>.md` |
| User journeys | `docs/app-workflows.md` |
| System layout, deployments | `ARCHITECTURE.md` |
| Dev or testing process | `docs/dev-workflows.md` |
| Setup or scope changes | `README.md` |
| Security changes | `docs/SECURITY.md` |
| Reliability changes | `docs/RELIABILITY.md` |
| Active work plans | `docs/exec-plans/active/` |
| Known tech debt | `docs/exec-plans/tech-debt-tracker.md` |

If documentation and implementation conflict, update docs in the same PR. Documentation rot destroys agent reliability.

## 10. Doc Map

| Topic | Location |
|-------|----------|
| System layout, data flows, boundaries | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Feature docs | [docs/features/](docs/features/) |
| User journeys | [docs/app-workflows.md](docs/app-workflows.md) |
| Engineering workflows and testing | [docs/dev-workflows.md](docs/dev-workflows.md) |
| Security principles | [docs/SECURITY.md](docs/SECURITY.md) |
| Reliability expectations | [docs/RELIABILITY.md](docs/RELIABILITY.md) |
| Execution plans | [docs/exec-plans/](docs/exec-plans/) |
| Tech debt | [docs/exec-plans/tech-debt-tracker.md](docs/exec-plans/tech-debt-tracker.md) |

## 11. When Unsure

- Prefer boring, stable libraries
- Prefer small PRs over large changes
- Add tests with every change
- Never bypass lint rules without explicit instruction
- Ask before making destructive or irreversible changes
