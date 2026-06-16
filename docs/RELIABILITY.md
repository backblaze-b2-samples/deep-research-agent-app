<!-- last_verified: 2026-06-11 -->
# Reliability

Reliability expectations and practices for this project.

## Research Runs (background jobs)

- A research run executes in a FastAPI `BackgroundTask`. `POST /research` returns
  immediately with status `pending`; the frontend polls `GET /research/{id}`.
- **Status is derived from B2 object existence** (`report.json.status` + presence
  of `report.md`) — there is no job queue or database. A process restart loses
  in-flight runs (a known v2 item: a persistent job store — see the tech-debt
  tracker), but completed work is durable on B2 because artifacts are written
  incrementally as the agent reads each source.
- Any exception during a run is caught and recorded as status `failed` with the
  error on `report.json`, plus a `.failed` marker key — failures never silently
  hang the UI.

## Partial-Failure Tolerance

- **Screenshot failures are non-fatal.** If a page renders but can't be
  screenshotted, the HTML and readable text are still cached and the source is
  recorded with `has_screenshot=false`. One bad page never kills a run.
- A page that can't be fetched at all (timeout, blocked URL) returns an error
  string to the model, which moves on to other sources.

## Depth Bounds and Timeouts

- `RESEARCH_MAX_SEARCHES` caps bundled web searches per run (default 8).
- `RESEARCH_MAX_SOURCES` caps pages fetched/cached per run (default 8); once
  reached, the model is told to write the report.
- `FETCH_TIMEOUT_MS` / `SCREENSHOT_TIMEOUT_MS` bound each page render; oversized
  HTML is truncated to `FETCH_MAX_BYTES` before caching.

## Health Checks

- `GET /health` verifies B2 connectivity and returns `healthy` or `degraded`
- Health endpoint is always available, even when B2 is down

## Error Handling

- HTTP handlers return structured error responses with appropriate status codes
- External service failures (B2) are caught and surfaced as 500/503 responses
- No unhandled exceptions leak stack traces to clients

## Logging

- Structured JSON logging via Python stdlib
- Every request gets a `request_id` for tracing
- Log levels: ERROR for failures, WARNING for degraded state, INFO for requests

## Observability

- Request timing middleware logs duration for every request
- `/metrics` endpoint exposes basic Prometheus-format counters
- Upload success/failure counts tracked

## Graceful Degradation

- File listing returns empty list (not error) when B2 has no objects
- Metadata extraction failures don't block upload (return partial metadata)
- Frontend shows skeleton states while loading, error states on failure

## Deployment

- Railway health checks on `/health`
- Zero-downtime deploys via rolling updates
- Environment-specific configuration via env vars (no config files in prod)
