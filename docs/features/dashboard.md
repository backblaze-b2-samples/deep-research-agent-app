<!-- last_verified: 2026-06-11 -->
# Feature: Dashboard

## Purpose
Give an at-a-glance overview of the research library on Backblaze B2 — how much the agent has accumulated and the most recent threads.

## Used By
- UI: `/` page (dashboard home)
- API: `GET /research/stats`, `GET /research`

## Core Functions
- `apps/web/src/components/dashboard/stats-cards.tsx` — 4 research stat cards
- `apps/web/src/components/dashboard/recent-research.tsx` — most recent threads
- `apps/web/src/lib/api-client.ts` — `getResearchStats()`, `getResearchLibrary()`
- `services/api/app/runtime/research.py` — `GET /research/stats` handler
- `services/api/app/service/library.py` — `get_stats()` business logic (aggregates over `research/`)
- `services/api/app/repo/b2_research.py` — `list_keys()`, `list_research_ids()` data access

## Canonical Files
- Stat cards: `apps/web/src/components/dashboard/stats-cards.tsx`
- Stats logic: `services/api/app/service/library.py`

## Inputs
- None (dashboard loads data automatically)

## Outputs
- `GET /research/stats` → `ResearchStats` (total_research, total_sources, total_screenshots, total_storage_bytes, total_storage_human, research_today)
- `GET /research?limit=8` → `ResearchSummary[]` for the recent-research list (newest-first)

## Flow
- Page loads → two parallel API calls (stats, recent research)
- Stat cards show: Research Threads, Sources Cached, Screenshots, Storage on B2
- Recent research list shows the latest threads with status badge, source count, and date
- "New research" button links to `/research`

## Edge Cases
- API unavailable → cards/list render an inline `ErrorState` with Retry (never fake zeros)
- No research yet → cards show 0 / "0 B", list shows an empty state
- Large library → stats paginate through all `research/` objects via `ContinuationToken`

## UX States
- Loading: skeleton placeholders for cards and list
- Empty: "No research yet" with a pointer to the Research page
- Error: `ErrorState` with Retry
- Loaded: populated cards + recent list

## Verification
- Test files: `services/api/tests/test_research_service.py` (`test_stats_counts_research_and_screenshots`)
- Required cases: stats with research, screenshot counting, storage aggregation
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green, no ruff/eslint violations

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [App Workflows](../app-workflows.md)
