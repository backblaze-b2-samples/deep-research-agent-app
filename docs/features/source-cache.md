<!-- last_verified: 2026-06-11 -->
# Feature: Source Caching on B2

## Purpose
Cache every page the agent reads on Backblaze B2 as raw HTML, a readable-text extraction, and a full-page screenshot — with provenance metadata — so B2 becomes the agent's durable memory.

## Used By
- UI: `/research/[id]` source cards (preview cached artifacts)
- API: executed inside the agent loop; `GET /research/{id}/sources`, `GET /research/{id}/sources/{sid}/{artifact}/preview`
- Job: the `fetch_source` tool call, executed by `service.research`

## Core Functions
- `services/api/app/repo/browser.py` — `fetch_page()` (Playwright render + screenshot, trafilatura extract, SSRF guard)
- `services/api/app/service/research.py` — `_cache_source()` (writes artifacts to B2, returns text to the model)
- `services/api/app/repo/b2_research.py` — `put_bytes()`, `put_text()`, `put_json()`, `source_key()`, `presign()`

## Canonical Files
- Fetch/extract/screenshot: `services/api/app/repo/browser.py`
- Caching orchestration: `services/api/app/service/research.py`

## Inputs
- url: string (from the model's `fetch_source` tool call)
- limits: `FETCH_TIMEOUT_MS`, `SCREENSHOT_TIMEOUT_MS`, `FETCH_MAX_BYTES`, viewport dims (settings)

## Outputs
- `research/<id>/sources/<sid>/page.html` — rendered HTML (capped to `fetch_max_bytes`)
- `research/<id>/sources/<sid>/page.md` — readable text (Markdown)
- `research/<id>/sources/<sid>/screenshot.png` — full-page PNG (may be absent)
- `research/<id>/sources/<sid>/meta.json` — `Source` provenance (url, title, fetched_at, sha256, byte sizes)
- the `Source` is appended to `report.json` incrementally

## Flow
- The model calls `fetch_source(url)`
- `browser.fetch_page()` validates the URL (SSRF), navigates, captures HTML, extracts Markdown, screenshots
- `_cache_source()` writes the four artifacts to B2 under a fresh `source_id`, appends the `Source` to `report.json`, and returns the (truncated) text + `source_id` to the model
- Source cards in the UI request presigned URLs to preview the cached page/screenshot

## Edge Cases
- Private/loopback/non-http(s) URL → `UnsafeUrlError`, nothing cached, model told it was refused
- Page fails to load → RuntimeError, nothing cached, model told it failed
- Screenshot fails → HTML + text still cached, `has_screenshot=false` (non-fatal)
- Oversized HTML → truncated to `fetch_max_bytes` before caching

## UX States
- Source cards: external link, fetched time, HTML/text sizes, buttons for screenshot / cached text / cached HTML
- "No screenshot" indicator when a screenshot was not captured

## Verification
- Test files: `services/api/tests/test_research_service.py` (`test_run_research_caches_sources_and_report`, `test_screenshot_failure_is_non_fatal`, `test_unsafe_url_is_skipped_not_fatal`)
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: artifacts asserted present/absent under `research/<id>/sources/<sid>/`

## Related Docs
- [Research Agent](research-agent.md)
- [docs/SECURITY.md](../SECURITY.md)
- [docs/RELIABILITY.md](../RELIABILITY.md)
