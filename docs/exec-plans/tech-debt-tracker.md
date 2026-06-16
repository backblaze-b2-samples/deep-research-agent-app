<!-- last_verified: 2026-06-11 -->
# Tech Debt Tracker

Known tech debt items. Agents update this when they discover or create tech debt.

## Deep Research Agent — v2 backlog

| Description | Impact | Proposed Resolution | Priority | Status |
|---|---|---|---|---|
| Search is keyword/metadata only | Misses semantically related research | Add semantic search via Voyage AI embeddings (Anthropic has no embeddings API → a 2nd provider/key); index source text + reports | Medium | Open (deferred from v1) |
| In-flight runs lost on process restart | A crash mid-run leaves status `running` forever | Add a persistent job store (e.g. a `jobs/` prefix on B2 or a small queue) and a startup reconciler that fails orphaned runs | Medium | Open |
| Progress is poll-based (2s `refetchInterval`) | Extra requests; coarse-grained updates | Stream progress via SSE from the background run instead of polling | Low | Open |
| `thread.json` is reserved but unused | Turns are tracked in `report.json` only | Either populate `thread.json` or drop it from the prefix layout | Low | Open |

## Inherited starter-kit items

| Description | Impact | Proposed Resolution | Priority | Status |
|---|---|---|---|---|
| `datetime.utcnow()` deprecated in Python 3.12+ | Naive datetimes, future breakage | Replace with `datetime.now(UTC)` in `repo/b2_client.py`, `service/metadata.py` | High | Resolved |
| S3 client recreated on every API call | Connection pool wasted, added latency | Cache client as module-level singleton via `lru_cache` | High | Resolved |
| `get_upload_stats()` pagination broken at 1000 objects | Stats silently wrong for large buckets | Check `IsTruncated` + use `ContinuationToken` | High | Resolved |
| `record_upload()` never called | `/metrics` always reports 0 uploads | Call from `runtime/upload.py` after successful upload | Medium | Resolved |
| Metrics counters not thread-safe | Race conditions under concurrent requests | Use `threading.Lock` (matches `service/files.py` pattern) | Medium | Resolved |
| `_humanize_bytes` duplicated in Python (repo + service) | DRY violation, drift risk | Extract to `app/types/formatting.py` shared util | Medium | Resolved |
| `humanizeBytes` duplicated in TypeScript | DRY violation | Extract to `lib/utils.ts` | Low | Open |
| `formatDate` duplicated in TypeScript | DRY violation | Extract to `lib/utils.ts` | Low | Open |
| No test harness for feature specs | No automated verification | Add pytest fixtures + test files per feature | Medium | Resolved (partial — tests added for upload, files, activity, errors) |
