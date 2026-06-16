<!-- last_verified: 2026-06-11 -->
# Feature: Search Across Research

## Purpose
Find past research by keyword across thread questions, report bodies, and the extracted readable text of cached sources.

## Used By
- UI: `/library` search box
- API: `GET /research/search?q=`

## Core Functions
- `apps/web/src/lib/queries.ts` — `useResearchSearch()`
- `services/api/app/service/research_search.py` — `search()` (substring/keyword matching + snippets)
- `services/api/app/repo/b2_research.py` — reads `report.json`, `report.md`, source `page.md`

## Canonical Files
- Search service: `services/api/app/service/research_search.py`

## Inputs
- q: string (query)
- limit: int (default 50)

## Outputs
- `GET /research/search?q=` → `ResearchSearchHit[]` (research_id, question, status, created_at, matched_in, snippet)

## Flow
- For each thread: match the question first (highest signal), then the report body, then source titles / extracted text
- The first match per thread wins; results are ranked newest-first
- Each hit shows where it matched and a short snippet with the term in context

## Edge Cases
- Empty query → no results (search disabled until a non-empty query)
- No matches → empty state in the UI
- v1 is keyword/metadata only; semantic search (Voyage embeddings) is a tracked v2 item — see [tech-debt-tracker](../exec-plans/tech-debt-tracker.md). Anthropic has no embeddings API, so semantic search would add a second provider/key and is intentionally deferred.

## UX States
- Loading: skeleton
- Empty: "No matches"
- Loaded: list of hits, each linking to the thread

## Verification
- Test files: `services/api/tests/test_research_service.py` (`test_search_finds_by_question`)
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: a known question is found by a keyword in it

## Related Docs
- [Research Library](research-library.md)
- [docs/exec-plans/tech-debt-tracker.md](../exec-plans/tech-debt-tracker.md)
