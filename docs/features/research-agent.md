<!-- last_verified: 2026-06-11 -->
# Feature: Research Agent

## Purpose
Turn a question into a long-form, cited report by running a real Claude Sonnet 4.6 tool-use loop that plans, searches the web, reads sources, and writes the report.

## Used By
- UI: `/research` (ask form), `/research/[id]` (status + report)
- API: `POST /research`, `GET /research/{id}`
- Job: FastAPI `BackgroundTask` running `service.research.run_research`

## Core Functions
- `services/api/app/service/research.py` — `create_research()`, `run_research()` (the manual loop)
- `services/api/app/repo/llm_client.py` — `create_turn()`, `container_id()`, `extract_text()`, `iter_tool_uses()`, tool defs, system prompt
- `services/api/app/repo/browser.py` — `fetch_page()` (executes the `fetch_source` tool)
- `services/api/app/repo/b2_research.py` — persists `report.json` / `report.md` and source artifacts

## Canonical Files
- Loop orchestration: `services/api/app/service/research.py`
- Model wrapper: `services/api/app/repo/llm_client.py`

## Inputs
- question: string (POST body, ≤ 2000 chars)
- settings: `ANTHROPIC_MODEL`, `RESEARCH_MAX_SEARCHES`, `RESEARCH_MAX_SOURCES`, `RESEARCH_EFFORT`

## Outputs
- `report.md` (Markdown report with inline citations) + `report.json` (`ReportMeta`) on B2
- cached source artifacts (see [source-cache.md](source-cache.md))
- status transitions pending → running → complete (or failed)

## Flow
- `POST /research` writes `report.json` (status=pending) and schedules a background run
- The run sets status=running, then loops model turns:
  - the model uses bundled `web_search` (server-side) to discover sources; that tool runs in a code-execution container, so once it fires the loop captures `message.container.id` and threads it back into every later `create_turn` (the API requires `container` while a server tool use is pending)
  - the model calls `fetch_source(url)`; the service executes it (render + cache to B2) and returns the readable text + `source_id`
  - depth bounds cap searches/sources; a budget message tells the model to write the report
- When the model stops calling tools, its text is the report → written to `report.md`, status=complete
- Tools given to Claude: native `web_search_20260209` (bundled) + custom `fetch_source`

## Edge Cases
- A blocked or unloadable URL → error string returned to the model; run continues
- Source budget reached → model is told to stop fetching and write
- Any exception in the loop → status=failed, `report.json.error` set, a `.failed` marker written
- Missing `ANTHROPIC_API_KEY` → `llm_client` raises at first turn → status=failed

## UX States
- Loading/Running: `RunStatus` shows sources cached so far; the page polls every 2s
- Error: failed runs render the recorded error
- Loaded: the rendered report + cached sources

## Verification
- Test files: `services/api/tests/test_research_service.py`
- Required cases: caches sources + report, blocked URL non-fatal, screenshot failure non-fatal, failure → status=failed
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest green; artifacts asserted under `research/<id>/`

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [Source Caching on B2](source-cache.md)
- [Follow-up Chains](follow-up-chains.md)
- [docs/SECURITY.md](../SECURITY.md)
