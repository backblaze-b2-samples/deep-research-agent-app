<!-- last_verified: 2026-06-16 -->
# Feature: Report Viewer

## Purpose
Render a research thread as a full conversation — every turn's question paired with the Markdown report it produced (inline citations) — alongside the cached sources it was built from. Follow-ups no longer hide earlier turns.

## Used By
- UI: `/research/[id]`
- API: `GET /research/{id}` (detail), `GET /research/{id}/sources/{sid}/{artifact}/preview`

## Core Functions
- `apps/web/src/components/research/conversation-view.tsx` — renders the whole thread turn by turn (question bubble + report), plus the in-flight/failed turn
- `apps/web/src/components/research/report-view.tsx` — `react-markdown` + `remark-gfm` renderer (used per turn)
- `apps/web/src/components/research/source-card.tsx` — cached-source previews
- `apps/web/src/lib/queries.ts` — `useResearch()` (polls while running)
- `services/api/app/service/report.py` — `get_detail()`, `get_sources()`, `get_source_artifact_url()`

## Canonical Files
- Conversation renderer: `apps/web/src/components/research/conversation-view.tsx`
- Per-report renderer: `apps/web/src/components/research/report-view.tsx`
- Report service: `services/api/app/service/report.py`

## Inputs
- research_id: string (route param)

## Outputs
- `GET /research/{id}` -> `ResearchDetail` (`meta` + `report_markdown` (latest) + `turns[]`, each a `ResearchTurnView` with its own `report_markdown`)
- `GET /research/{id}/sources/{sid}/{artifact}/preview` -> `{ url }` (presigned, 10-min)

## Flow
- The page fetches the detail; while `pending`/`running` it polls every 2s
- The page title is the thread's *root* question (`turns[0].question`); the status badge reflects the latest run
- `ConversationView` renders every completed turn oldest-first — each as a question bubble followed by that turn's report — then the active question + `RunStatus` (if running) or the error (if failed)
- The sidebar lists cached sources (aggregated across the whole thread); each card opens its cached screenshot / text / HTML via presigned URLs
- A follow-up box is shown for completed reports (see follow-up-chains.md)

## Edge Cases
- `failed` status -> shows prior turns, then the failed question + the recorded error
- `complete` with no turns -> "No report was produced."
- A turn whose per-turn report is missing (legacy threads) -> the most recent such turn falls back to `report.md`; older turns show "The report for this turn is no longer available."
- Artifact preview validates the source belongs to the thread before presigning (no arbitrary-key reads)

## UX States
- Loading: skeletons
- Running: prior turns + active question + `RunStatus` with live source count
- Error/Failed: prior turns + active question + `ErrorState`
- Loaded: full conversation (question bubbles + rendered reports) + source cards

## Verification
- Test files: `services/api/tests/test_research_service.py` (`test_run_research_caches_sources_and_report`, `test_follow_up_preserves_whole_conversation`, `test_legacy_thread_without_per_turn_report_falls_back`)
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: `turns[]` returned oldest-first with a `report_markdown` per turn; `report_markdown` still holds the latest report; artifact preview rejects mismatched ids

## Related Docs
- [Research Agent](research-agent.md)
- [Source Caching on B2](source-cache.md)
- [Follow-up Chains](follow-up-chains.md)
