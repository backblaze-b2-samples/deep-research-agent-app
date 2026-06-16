<!-- last_verified: 2026-06-16 -->
# Feature: Follow-up Chains

## Purpose
Let a user ask follow-up questions that build on a thread's prior report, which is loaded as cached context for the next agentic run.

## Used By
- UI: `/research/[id]` follow-up box
- API: `POST /research/{id}/follow-up`
- Job: another `BackgroundTask` run of `service.research.run_research`

## Core Functions
- `apps/web/src/components/research/follow-up-box.tsx` — the follow-up form
- `apps/web/src/lib/queries.ts` — `useFollowUp()`
- `services/api/app/service/research.py` — `add_follow_up()`, `_initial_messages()` (loads prior report)

## Canonical Files
- Follow-up service path: `services/api/app/service/research.py`

## Inputs
- research_id: string (route param)
- question: string (POST body)

## Outputs
- a new turn appended to `report.json.turns[]`
- an updated `report.md` (latest) **and** a durable per-turn copy at `reports/<report_id>.md`
- status reset to pending → running → complete

## Flow
- `POST /research/{id}/follow-up` marks the thread pending and schedules a run
- `_initial_messages()` prepends the prior `report.md` as a prompt-cached context block
- the agent runs the same loop, may fetch new sources, and writes an updated report
- `_finalize()` writes both `report.md` and `reports/<report_id>.md`, then appends the turn (question + report_id + source_ids) to `report.json`
- because every turn keeps its own report, the detail view (`GET /research/{id}` → `ResearchDetail.turns[]`) shows the full conversation: each prior question and the answer it produced, not just the latest

## Edge Cases
- Follow-up on an unknown id → 404
- Prior report missing → the run proceeds as a fresh research on the new question
- Follow-up while a run is in flight is discouraged by the UI (box only shows on `complete`)
- Legacy threads (created before per-turn reports) have no `reports/<report_id>.md`; `get_detail` falls back to `report.md` for the most recent turn so the latest answer still renders

## UX States
- The full conversation stays visible across follow-ups — prior questions and answers don't disappear
- The follow-up box renders only for completed reports
- Submitting flips the thread back to running; the active question shows with live status while the page's poll resumes

## Verification
- Test files: `services/api/tests/test_research_service.py` (`test_follow_up_preserves_whole_conversation`, plus run + status coverage)
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: turns accumulate; each turn's report persists under `reports/<report_id>.md`; prior report is loaded as context; `get_detail` returns the full conversation

## Related Docs
- [Research Agent](research-agent.md)
- [Report Viewer](report-viewer.md)
