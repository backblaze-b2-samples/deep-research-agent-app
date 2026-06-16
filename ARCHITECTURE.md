<!-- last_verified: 2026-06-11 -->
# Architecture

The **Deep Research Agent** turns a question into a long-form, cited report by
running a real Claude Sonnet 4.6 tool-use loop, and caches every artifact it
touches on Backblaze B2. B2 is the agent's durable memory.

## Components

- **apps/web/** — Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
  - Research page (ask a question; recent research) and report detail (polls for status; report + cached sources + follow-up box)
  - Research Library — scoped explorer over the `research/` prefix, with search and delete
  - Dashboard with research metrics (threads, sources cached, screenshots, storage on B2)
  - Kept starter surfaces: full-bucket File browser + Upload; dark mode via `next-themes`
- **services/api/** — FastAPI backend (layered architecture)
  - The research agent loop (Anthropic tool-use), web search (bundled), and page fetching/caching
  - B2 S3 integration via boto3, scoped to the `research/` prefix
  - Background-task execution; status derived from B2 object existence (no DB)
  - Health check, structured JSON logging with request tracing, Prometheus metrics
  - Kept: file upload/listing/deletion + metadata extraction (images, PDFs)
- **packages/shared/** — TypeScript type definitions
  - Mirrors Pydantic models from the API (incl. Research/Source/Report/Thread/Status)
  - Consumed by `apps/web/` as workspace dependency

### Agent components (the core feature)

- **repo/llm_client.py** — the only module that imports `anthropic`. Exposes a thin per-turn interface so the loop can live in the service layer. Configures model, adaptive thinking, prompt caching on the system prompt + accumulated context, and the two tools given to Claude: server-side `web_search` (bundled) and the client-side `fetch_source`.
- **repo/browser.py** — the only module that imports `playwright`/`trafilatura`. Renders a page in headless Chromium, extracts readable Markdown, and captures a full-page screenshot. Enforces SSRF guards (blocks private/loopback/non-http(s)) and a failed screenshot is non-fatal.
- **repo/b2_research.py** — B2 object operations scoped to `research/`. Reads/writes JSON, text, and bytes; lists threads; deletes a thread's prefix; presigns artifact URLs.
- **service/research.py** — the *manual* agentic loop: it drives model turns, intercepts each `fetch_source` to cache the page to B2 and feed the text back, enforces depth bounds (`research_max_searches`/`research_max_sources`), updates status, and writes the final report. Runs in a FastAPI `BackgroundTask`.

## Backend Layering

The API follows a strict layered architecture:

```
types/     Pydantic models — no logic, no imports from other layers
  |
config/    Settings (pydantic-settings) — depends only on types
  |
repo/      Data access (boto3 B2 client) — no business logic
  |
service/   Business logic — calls repo, returns types
  |
runtime/   FastAPI routes — calls service, never repo directly
```

### Layering Rules

1. Dependencies flow downward only: `types` -> `config` -> `repo` -> `service` -> `runtime`
2. No backward imports (e.g., service must not import from runtime)
3. `boto3` only allowed in `repo/` layer
4. `anthropic`, `playwright`, `trafilatura`, `httpx` only allowed in `repo/` layer (the agent's external I/O is wrapped behind `llm_client.py` and `browser.py`)
5. All boundary data uses Pydantic models (no raw dicts across layers)
6. Each file stays under 300 lines

### Directory Structure

```
services/api/
  main.py                  App entrypoint, middleware, router registration
  app/
    types/                 Pydantic models (FileMetadata, UploadStats, etc.)
    config/                Settings loaded from environment
    repo/                  B2 S3 client (data access layer)
    service/               Business logic (upload, files, metadata)
    runtime/               FastAPI route handlers
  tests/                   pytest tests (structural + integration)
```

## Boundary Invariants

- **No external SDK leakage**: `boto3` is only imported in `app/repo/`. All other layers interact with B2 through the repo interface.
- **No raw dicts at boundaries**: All data crossing layer boundaries uses typed Pydantic models.
- **No mutable globals**: Configuration is read-only after init. No module-level mutable state shared between layers.
- **Validated inputs**: All HTTP inputs validated by FastAPI/Pydantic. All file keys validated against prefix allowlist.

## Deployment

- **Local dev** — `pnpm dev` runs both services via `concurrently`
  - Web: `localhost:3000`
  - API: `localhost:8000`
- **Railway** — two services from the same repo
  - See `infra/railway/README.md` for configuration

## Data Stores

- **Backblaze B2** — object storage (S3-compatible API), the sole data store and the agent's memory.
  - All app artifacts live under the `research/` prefix:

    ```
    research/<research_id>/
      report.json     ReportMeta (status, sources[], turns[]) — status source of truth
      report.md       latest long-form Markdown report (inline citations)
      reports/<report_id>.md  per-turn report — preserves the full conversation history
      thread.json     follow-up chain (reserved)
      sources/<source_id>/
        page.html       cached rendered HTML
        page.md         extracted readable text (Markdown)
        screenshot.png  Playwright full-page screenshot (may be absent)
        meta.json       provenance (url, title, fetched_at, sha256, byte sizes)
    ```

  - **Status is derived from B2 object existence** — `report.json.status` plus the presence of `report.md`. No application database. The frontend polls while a run is `pending`/`running`.
  - S3 ops exercised: `put_object`, `get_object`, `head_object`, `list_objects_v2` (Prefix/Delimiter), `delete_objects`, `generate_presigned_url` — all scoped to `research/`.

## External Services

- **Backblaze B2 S3 API** — artifact storage, retrieval, deletion, presigned URLs (custom user agent `b2ai-deep-research-agent-app`, signature v4, no b2-native API).
- **Anthropic API** — Claude Sonnet 4.6 powers the agent's reasoning, tool orchestration, and report writing, plus the bundled server-side `web_search` tool. Wrapped in `repo/llm_client.py`.
- **The open web** — the agent fetches arbitrary source pages via Playwright Chromium (`repo/browser.py`). Fetched content is untrusted; see SECURITY.md for SSRF + prompt-injection handling.

## Trust Boundaries

See [docs/SECURITY.md](docs/SECURITY.md) for full security documentation.

- **Frontend -> API** — CORS-restricted to configured origins
- **API -> B2** — authenticated via application keys, signature v4
- **API -> Anthropic** — authenticated via `ANTHROPIC_API_KEY` (server-side only; never sent to the browser)
- **API -> open web** — the agent fetches arbitrary URLs; `browser.py` blocks private/loopback/non-http(s) targets (SSRF) and caps size/timeout. Fetched page content is untrusted *data*, never instructions (prompt-injection note in SECURITY.md).
- **Client -> B2** — presigned URLs for previewing cached artifacts (10-min expiry)

## Data Flows

- **Research run**: Browser -> `POST /research` -> service writes `report.json` (status=pending) to B2 and schedules a BackgroundTask -> the task runs the manual Claude loop: model turn -> (server-side `web_search`) -> model requests `fetch_source(url)` -> service renders the page, caches `page.html`/`page.md`/`screenshot.png`/`meta.json` under `research/<id>/sources/<sid>/`, appends the Source to `report.json`, returns the text -> repeat until the model stops -> service writes `report.md` (latest) **and** the durable per-turn copy `reports/<report_id>.md`, then marks `report.json` complete. The browser polls `GET /research/{id}` for status the whole time.
- **Follow-up**: Browser -> `POST /research/{id}/follow-up` -> service marks the thread pending and schedules another run that loads the prior `report.md` as cached context -> produces an updated report and appends a turn. Each turn keeps its own `reports/<report_id>.md`, so `GET /research/{id}` returns the whole conversation (every question + its report) rather than only the latest answer.
- **Library / search**: Browser -> `GET /research` (list) or `GET /research/search?q=` -> service lists/reads under `research/` -> returns summaries / ranked hits.
- **Artifact preview**: Browser -> `GET /research/{id}/sources/{sid}/{artifact}/preview` -> service validates the source belongs to the thread -> repo presigns the cached object (10-min expiry).
- **Delete**: Browser -> `DELETE /research/{id}` -> service deletes only `research/<id>/...` (scoped; never touches shared data).
- Kept starter flows (Upload / List / Download / Delete on `/files`) are unchanged.

## Observability

- Structured JSON logging on all requests with `request_id`
- Request timing middleware (logs duration per request)
- `/metrics` endpoint (Prometheus format: request count, latency, upload count)
- `/health` endpoint (B2 connectivity check)

## Canonical Files

- Agent loop orchestration: `services/api/app/service/research.py`
- Anthropic wrapper (repo): `services/api/app/repo/llm_client.py`
- Browser fetch/extract/screenshot (repo): `services/api/app/repo/browser.py`
- B2 prefix-scoped access (repo): `services/api/app/repo/b2_research.py`
- Research routes (runtime): `services/api/app/runtime/research.py`
- Pydantic models: `services/api/app/types/research.py` (+ kept `files.py`, `upload.py`, `stats.py`, `formatting.py`)
- B2 client + custom user agent: `services/api/app/repo/b2_client.py`
- Config (pydantic-settings): `services/api/app/config/settings.py`
- Structural tests: `services/api/tests/test_structure.py`; agent tests: `tests/test_research_service.py`
- Frontend API client / hooks: `apps/web/src/lib/api-client.ts`, `apps/web/src/lib/queries.ts`
- Shared TypeScript types: `packages/shared/src/types.ts`

## Core Features

- [Research Agent](docs/features/research-agent.md)
- [Source Caching on B2](docs/features/source-cache.md)
- [Research Library](docs/features/research-library.md)
- [Report Viewer](docs/features/report-viewer.md)
- [Follow-up Chains](docs/features/follow-up-chains.md)
- [Search Across Research](docs/features/research-search.md)
- [Dashboard](docs/features/dashboard.md)
- Kept: [File Upload](docs/features/file-upload.md), [File Browser](docs/features/file-browser.md), [Metadata Extraction](docs/features/metadata-extraction.md)

## References

- [docs/SECURITY.md](docs/SECURITY.md) — security principles and implementation
- [docs/RELIABILITY.md](docs/RELIABILITY.md) — reliability expectations
- [AGENTS.md](AGENTS.md) — architectural invariants and agent instructions
