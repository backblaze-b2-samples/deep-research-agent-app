# Plan: Show the full multi-turn conversation on a research thread

## Problem
On `/research/[id]` a multi-turn thread only showed the latest answer. Follow-ups
overwrote `meta.question` and `report.md`, and the detail page rendered just those
two — so prior questions and prior reports were invisible. The per-turn report
markdown was never even persisted (a `report_id` was generated but nothing was
stored under it), so there was no history to render.

## Scope
- Persist each turn's report under `research/<id>/reports/<report_id>.md` (keep
  `report.md` as the latest, used for follow-up context + search).
- Return the whole conversation from `GET /research/{id}` as `ResearchDetail.turns[]`
  (each a `ResearchTurnView` with its own `report_markdown`).
- Render the thread as a conversation (question bubble + report per turn), with the
  in-flight/failed turn appended; title the page by the thread's root question.
- Graceful fallback for legacy threads (no per-turn file): the most recent turn
  falls back to `report.md`.
- Docs + tests in the same change.

## Steps
1. `repo/b2_research.py` — add `turn_report_key()`; update layout docstring.
2. `service/research.py::_finalize` — write `report.md` *and* `reports/<report_id>.md`.
3. `types/research.py` — add `ResearchTurnView`; add `turns[]` to `ResearchDetail`.
4. `service/report.py::get_detail` — build `turns[]` from per-turn reports with the
   legacy fallback for the most recent turn.
5. `packages/shared/src/types.ts` — mirror `ResearchTurnView` + `ResearchDetail.turns`.
6. `components/research/conversation-view.tsx` — new; renders the conversation.
7. `app/research/[id]/page.tsx` — use `ConversationView`; title = root question.
8. Tests: `test_follow_up_preserves_whole_conversation`,
   `test_legacy_thread_without_per_turn_report_falls_back`.
9. Docs: AGENTS.md + ARCHITECTURE.md B2 layout/flow; report-viewer.md;
   follow-up-chains.md.

## Verification
- `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure` — all green
  (34 backend tests pass), `pnpm build` type-checks.
