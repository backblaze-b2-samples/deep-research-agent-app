<!-- last_verified: 2026-06-11 -->
# Feature: Research Library

## Purpose
Browse every past research thread and its cached sources/screenshots — the sample-specific asset explorer scoped to the `research/` prefix (distinct from the kept full-bucket `/files` explorer).

## Used By
- UI: `/library`
- API: `GET /research`, `GET /research/search?q=`, `DELETE /research/{id}`

## Core Functions
- `apps/web/src/app/library/page.tsx` — library grid + search box
- `apps/web/src/components/library/research-grid.tsx` — cards with status, counts, delete
- `services/api/app/service/library.py` — `list_research()`, `delete_research()`, `get_stats()`
- `services/api/app/repo/b2_research.py` — `list_research_ids()`, `delete_research()` (prefix-scoped)

## Canonical Files
- Library page: `apps/web/src/app/library/page.tsx`
- Library service: `services/api/app/service/library.py`

## Inputs
- limit: int (list)
- q: string (search; see [research-search.md](research-search.md))
- research_id: string (delete)

## Outputs
- `GET /research` → `ResearchSummary[]` (newest-first)
- `DELETE /research/{id}` → `{ deleted, research_id, objects }`

## Flow
- `/library` lists all threads as cards (question, status badge, source/turn counts, date)
- Typing in the search box switches to ranked search results
- Each card links to `/research/[id]`; the trash button confirms, then deletes the thread

## Edge Cases
- Empty library → empty state pointing to `/research`
- Delete scoped strictly to `research/<id>/...` — never affects other apps' data or other threads
- Delete of a non-existent id → 404

## UX States
- Loading: skeleton grid
- Empty: "Your research library is empty"
- Error: `ErrorState` with Retry
- Loaded: grid of research cards

## Verification
- Test files: `services/api/tests/test_research_service.py` (`test_delete_is_scoped_to_prefix`)
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: deleting one thread leaves siblings and unrelated keys intact

## Related Docs
- [Search Across Research](research-search.md)
- [Report Viewer](report-viewer.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
