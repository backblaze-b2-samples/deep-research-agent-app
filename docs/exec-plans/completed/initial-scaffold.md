# Scaffold plan — `deep-research-agent-app`

Source of truth: `.claude/scratch/vcsk-9fd111d7-68a1-4904-b234-03df672f3261/`
(fresh `vibe-coding-starter-kit` clone). Built on the Next.js (`apps/web`) +
FastAPI (`services/api`, layered `types→config→repo→service→runtime`) +
`packages/shared` monorepo.

User decisions (Phase 1): agent model **Claude Sonnet 4.6**; **include
Playwright screenshots** of sources; **follow-up question chains** in v1.

---

## 1. Purpose

`deep-research-agent-app` is a deep-research agent that turns a question into a
long-form, cited report. The agent **plans → searches the web → fetches and
reads source pages → writes the report**, and **every artifact it touches — the
raw HTML of each source page, a readable-text extraction, a full-page
screenshot, and the final report — is cached on Backblaze B2**. Past research is
browsable and keyword-searchable, so a research library accumulates over time.
Follow-up questions reuse a thread's prior reports as context.

It is for developers evaluating B2 as **durable agent memory / an object store
for agent workflows**: cached pages, screenshots, and reports stack up fast, the
"research library" only grows, and the whole thing is S3-compatible. The B2
value prop on display is *agentic workloads writing many artifacts to cheap,
durable object storage and reading them back*.

The Claude agent is the **core** API (per `api-provider-selection.md`): it is
really wired — real Claude tool-use calls, real web searches, real pages and
reports written to B2. Cost is flagged and approved below.

---

## 2. Architecture delta from `vibe-coding-starter-kit`

The starter kit is the ceiling. It is already lean and almost everything it
ships is reused, so **TRIM is intentionally near-empty** — we *adapt* the
dashboard and *add* the research surfaces rather than strip.

| KEEP (as-is) | TRIM (remove) | ADD (new for this app) |
|---|---|---|
| `components/ui/**` (shadcn primitives), design tokens in `globals.css`, `/design` page + `components/design/**` | *(none)* | **Backend** `services/api/app/repo/llm_client.py` (Anthropic SDK wrapper), `repo/browser.py` (Playwright fetch + screenshot + text extract), `repo/b2_research.py` (B2 ops scoped to `research/` prefix) |
| **`/files` full-bucket explorer** — `app/files/`, `components/files/**`, `lib/file-tree.ts` + its sidebar entry **(NON-NEGOTIABLE KEEP)** | *(none)* | **Backend** `service/research.py` (agent loop orchestration), `service/library.py`, `service/report.py`, `service/research_search.py`; `runtime/research.py` (routes); `types/research.py` |
| `/upload` page + `components/upload/**` + sidebar entry | *(none)* | **Frontend** `app/research/page.tsx` (ask + recent), `app/research/[id]/page.tsx` (report + sources + follow-up box), `app/library/page.tsx` (**scoped explorer**), `components/research/**`, `components/library/**` |
| FastAPI layered skeleton, `main.py` shape, JSON logging, `/health`, `/metrics`, request-id middleware, `tests/test_structure.py` framework | *(none)* | **Frontend** rewritten `components/dashboard/**` (research metrics), markdown report renderer, follow-up UI; sidebar entries for **Research** + **Library** |
| TanStack Query layer (`lib/api-client.ts`, `lib/queries.ts`, `query-client.tsx`, `refresh-context.tsx`), `packages/shared` | *(none)* | **Shared** new TS types in `packages/shared/src/types.ts` (Research, Source, Report, Thread, Status) |
| Layout (`app-sidebar`, `header`, `health-banner`, `command-palette`, `theme-provider`), `app/settings`, error/loading/not-found | *(none)* | **Deps** `anthropic`, `playwright`, `trafilatura` (readable-text extraction), `react-markdown` + `remark-gfm` (report rendering); `httpx` if not already present |
| `infra/railway`, `scripts/dev.sh`, `scripts/pick-port.mjs`, `.pre-commit-config.yaml`, eslint/ruff configs | *(none)* | **Docs** new feature docs + rewritten AGENTS/ARCHITECTURE/README/SECURITY/RELIABILITY (see §5) |
| `docs/features/{file-browser,file-upload,metadata-extraction}.md` (still describe the kept Files/Upload surfaces) | *(none)* | **Tests** `tests/test_research_service.py` (mocked `llm_client` + `browser`); extend `test_structure.py` SDK allowlist |
| **Dashboard** `/` + `components/dashboard/**` are **ADAPTED** (per starter contract — the one screen meant to be rewritten), not kept verbatim | | `scripts/doctor.mjs` updated for new env vars + Playwright/Chromium preflight |

**Bucket-explorer rule satisfied:** the full-bucket `/files` explorer **stays**
(KEEP). The required sample-specific scoped explorer is the **Research Library**
(`/library`) — a view scoped to the `research/` prefix that browses past reports
and each report's cached sources/screenshots (analogous to the TTS sample's
audio "Library").

### B2 prefix / key layout (the app's own artifacts)

`RESEARCH_PREFIX = "research/"` (constant in the repo layer).

```
research/<research_id>/
  thread.json                 # follow-up chain: ordered turns [{question, report_id, source_ids, created_at}]
  report.md                   # latest long-form report (Markdown, inline citations)
  report.json                 # {question, model, status, sources[], created_at, turns[]}
  sources/<source_id>/
    page.html                 # cached raw (rendered) HTML
    page.md                   # extracted readable text (Markdown)
    screenshot.png            # Playwright full-page screenshot
    meta.json                 # {url, title, fetched_at, sha256, byte sizes}
```

Status is **derived from B2 object existence** (no DB — matches the
voice-memo/meeting-memory pattern): `report.json.status` field + presence of
`report.md` (`pending` → `running` → `complete`; a `.failed` marker key on
error). Frontend polls via `refetchInterval`.

### The agent loop (core API)

- `repo/llm_client.py` wraps the **`anthropic` SDK** — the only place it may be
  imported (structural test extended). Runs the agentic loop and the
  report-writing turn. Model from settings (`claude-sonnet-4-6`), adaptive
  thinking, `effort` from settings (default `medium`), prompt caching on the
  system prompt + accumulated source context.
- **Tools given to Claude:**
  - Server-side **`web_search_20260209`** (Anthropic native web search — *bundled*,
    one key, dynamic filtering on Sonnet 4.6) for discovery.
  - Custom client-side tool **`fetch_source(url)`** — the service executes it:
    `repo/browser.py` navigates with Playwright, captures rendered HTML +
    full-page PNG, extracts readable text (trafilatura), writes
    `page.html`/`page.md`/`screenshot.png`/`meta.json` to B2 under the research's
    `sources/` prefix, and returns the extracted text (truncated) + `source_id`
    to the agent. **This is what makes B2 the agent's memory.**
- Orchestrated as a **manual agentic loop** in `service/research.py` (not the
  auto `tool_runner`) so we can intercept `fetch_source` for B2 caching, enforce
  depth bounds (`research_max_searches`, `research_max_sources`), and update
  status. Final turn writes the report → B2.
- Runs in a FastAPI **`BackgroundTasks`** job. **Follow-ups** append a turn to
  `thread.json` and kick another background run that loads prior report(s) as
  context (prompt-cached), producing an updated/appended report.
- Playwright screenshots are **resilient**: a single page failing to render or
  screenshot logs and continues (HTML/text still cached, screenshot omitted) —
  one bad source never kills the run.

---

## 3. B2 surface (S3 operations exercised)

All via **boto3 / S3-compatible API**, signature v4, custom user agent — **no
b2-native API** (Standard #1 ✅).

| Operation | Where / why |
|---|---|
| `put_object` | cache `page.html`/`page.md`/`screenshot.png`/`meta.json`; write `report.md`/`report.json`/`thread.json` |
| `list_objects_v2` (Prefix) | Research Library listing, sources-per-research, dashboard stats — all scoped to `research/` |
| `head_object` | status checks (does `report.json` exist?), object metadata |
| `get_object` | load prior report/thread for follow-up context; render report; serve cached page/screenshot bodies |
| `generate_presigned_url` | download/preview screenshots, reports, cached pages (inherited Files/preview flow, 10-min expiry, attachment disposition) |
| `delete_object` | delete a research thread — **scoped to its `research/<id>/` prefix only** (honors CLAUDE.local.md: never wipe shared data) |

No b2-native calls. Custom user agent set on the single S3 client in
`repo/b2_client.py` (Standard #2 ✅).

---

## 4. Key features (seed README + `docs/features/` stubs)

1. **Research agent** — ask a question; the agent plans, web-searches, reads
   sources, and writes a cited long-form report (Claude Sonnet 4.6 tool-use loop).
2. **Source caching on B2** — every fetched page is cached as HTML + readable
   Markdown + a full-page screenshot, with provenance metadata.
3. **Research Library (scoped explorer)** — browse every past research thread and
   its cached sources/screenshots; the sample-specific asset explorer scoped to
   `research/`.
4. **Follow-up question chains** — ask follow-ups that build on a thread's prior
   reports (loaded as cached context).
5. **Search across past research** — keyword/metadata search over report titles,
   questions, and extracted source text (v1; semantic/embeddings is v2 — see §5).
6. **Report viewer** — rendered Markdown report with inline citations linking to
   the cached source pages/screenshots.

### External API provider (required record)

- **Provider:** Anthropic (Claude). **Model:** `claude-sonnet-4-6` — agent
  reasoning, tool orchestration, and report writing. Adaptive thinking; `effort`
  default `medium`; prompt caching on system prompt + accumulated context.
- **Tools:** native server-side `web_search_20260209` (bundled search — resolves
  the "BYO vs bundled" open question: **bundled**, one key) + custom client-side
  `fetch_source`.
- **Env var:** `ANTHROPIC_API_KEY` (provider-conventional; placeholder in
  `.env.example`; never committed). Settings also: `ANTHROPIC_MODEL`
  (default `claude-sonnet-4-6`), `RESEARCH_MAX_SEARCHES` (default 8),
  `RESEARCH_MAX_SOURCES` (default 8), `RESEARCH_EFFORT` (default `medium`),
  fetch/screenshot timeouts + screenshot viewport.
- **Estimated cost, one full demo run (incl. our own test runs):**
  **~$0.50 – $1.10**. Basis: Sonnet 4.6 at $3 / 1M input, $15 / 1M output;
  ~6–10 web searches at ~$0.01 each (~$10 / 1,000); reading ~6–10 pages
  (~10–20k tokens each) accumulates context but prompt caching bills re-reads at
  ~0.1×; report output ~3–10k tokens. **This is a core API and exceeds the
  peripheral <$1 budget — flagged and USER-APPROVED (Phase 1).** Tunable down via
  `RESEARCH_MAX_SEARCHES` / `RESEARCH_MAX_SOURCES`.
- **No Anthropic embeddings API exists** (they partner with Voyage AI) → "search
  across past research" is **keyword/metadata** in v1, single-key. Semantic
  search (Voyage embeddings, a 2nd key) is deferred to v2.

---

## 5. Doc transforms

**Rewrite:**
- `README.md` — hook (deep research agent on B2), "what you get", screenshot
  placeholders, data-flow diagram, quick start (B2 creds + `ANTHROPIC_API_KEY` +
  `playwright install chromium`), env table, features (links to new feature
  docs), tech stack (+ anthropic/playwright/trafilatura/react-markdown), commands,
  doc map.
- `AGENTS.md` — repo map (research surfaces, `llm_client`/`browser`/`b2_research`
  repos), B2 prefix table, invariants (+ "no `anthropic`/`playwright` SDK outside
  `repo/`"), commands (+ playwright install), doc map. Keep layering/quality/
  enforcement structure.
- `ARCHITECTURE.md` — components (agent service, browser/llm repos, research
  surfaces), layering unchanged, data flows (research run, follow-up, fetch+cache),
  external services (Anthropic API + web), data stores (B2 + prefix layout above).
- `docs/features/dashboard.md` — research metrics (threads, sources cached,
  screenshots, storage, recent research).

**Keep (still valid for kept surfaces):**
- `docs/features/file-browser.md`, `file-upload.md`, `metadata-extraction.md`.

**Add (new stubs from `_template.md`):**
- `docs/features/research-agent.md`, `source-cache.md`, `research-library.md`,
  `report-viewer.md`, `follow-up-chains.md`, `research-search.md`.
- Update `docs/app-workflows.md` (research + follow-up journeys),
  `docs/dev-workflows.md` (Playwright setup, Anthropic key, mocking `llm_client`/
  `browser` in tests).
- `docs/SECURITY.md` — add: `ANTHROPIC_API_KEY` handling; **SSRF guardrails on
  `fetch_source`** (agent fetches arbitrary URLs → block private/loopback IPs,
  cap size/timeout); **prompt-injection note** (fetched page content is untrusted
  data, not instructions); screenshot/file-size limits.
- `docs/RELIABILITY.md` — background-job behavior, partial-failure (screenshot
  fail → continue), depth bounds, fetch timeouts/retries.
- `docs/exec-plans/tech-debt-tracker.md` — v2 items: semantic search (Voyage
  embeddings), persistent job store, streaming progress (SSE) instead of polling.
- (Phase 5) this plan moves to `docs/exec-plans/completed/initial-scaffold.md`.

---

## 6. Rename table (`vibe-coding-starter-kit` → `deep-research-agent-app`)

| Form | From | To |
|---|---|---|
| kebab / repo slug | `vibe-coding-starter-kit` | `deep-research-agent-app` |
| snake (any Python ids) | `vibe_coding_starter_kit` | `deep_research_agent_app` |
| pnpm workspace pkgs | `@vibe-coding-starter-kit/web`, shared pkg | `@deep-research-agent-app/web`, `@deep-research-agent-app/shared` |
| `package.json` `name` (root + web + shared) | `vibe-coding-starter-kit*` | `deep-research-agent-app*` |
| Title Case (sidebar brand, README H1) | "Vibe Coding Starter Kit" / "OSS Starter Kit" | "Deep Research Agent" |
| FastAPI app title | "OSS Starter Kit API" | "Deep Research Agent API" |
| **`user_agent_extra`** (Standard #2) | `b2ai-oss-start` | `b2ai-deep-research-agent-app` |
| **UTM `utm_content`** (README + sidebar footer links) | `b2ai-oss-start` | `b2ai-deep-research-agent-app` |
| image filenames / workflow slugs / railway service names | `*starterkit*` / `*starter-kit*` | `*deep-research-agent-app*` |

### Standard #3 — env var rename (required; starter deviates)

| Starter (`.env.example`, `settings.py`, `main.py`, `doctor.mjs`) | New (standardized) |
|---|---|
| `B2_KEY_ID` / `settings.b2_key_id` | **`B2_APPLICATION_KEY_ID`** / `b2_application_key_id` |
| *(missing)* | **add `B2_REGION`** / `b2_region` |
| `B2_APPLICATION_KEY`, `B2_BUCKET_NAME`, `B2_ENDPOINT` | unchanged (already standard) |
| — add — | `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, `RESEARCH_MAX_SEARCHES`, `RESEARCH_MAX_SOURCES`, `RESEARCH_EFFORT` |

Touch points for the env rename: `.env.example`, `services/api/app/config/settings.py`,
`services/api/main.py` (`REQUIRED_B2_SETTINGS`, `PLACEHOLDER_VALUES`),
`services/api/app/repo/b2_client.py`, `scripts/doctor.mjs`, README setup section.

---

## Backend file map (for the builder)

- **types/** add `research.py` (`ResearchThread`, `ResearchTurn`, `Source`,
  `ReportMeta`, `ResearchStatus`); keep `files.py`/`upload.py`/`stats.py`/`formatting.py`.
- **config/** `settings.py`: env renames + new keys above.
- **repo/** add `llm_client.py` (anthropic), `browser.py` (playwright + trafilatura),
  `b2_research.py` (prefix-scoped ops); edit `b2_client.py` (settings rename, region,
  user agent → `b2ai-deep-research-agent-app`).
- **service/** add `research.py`, `library.py`, `report.py`, `research_search.py`;
  keep `files.py`/`upload.py`/`metadata.py`.
- **runtime/** add `research.py` — `POST /research`, `POST /research/{id}/follow-up`,
  `GET /research` (library), `GET /research/{id}` (status+report), `GET /research/{id}/sources`,
  `GET /research/search?q=`, `GET /research/stats`, `DELETE /research/{id}`; keep
  `files`/`upload`/`health`/`metrics`. Register router in `main.py`.
- **tests/** add `test_research_service.py` (mock `llm_client` + `browser`, assert
  artifacts written under `research/<id>/`); extend `test_structure.py` to allow
  `anthropic` + `playwright` + `trafilatura`/`httpx` **only in `repo/`**.

## Frontend file map (for the builder)

- **app/** add `research/page.tsx`, `research/[id]/page.tsx`, `library/page.tsx`;
  keep `files`/`upload`/`settings`/`design`/`page.tsx`.
- **components/** add `research/**` (ask-form, run-status, report-view, source-card,
  follow-up-box), `library/**` (research grid/list); rewrite `dashboard/**` for
  research metrics.
- **lib/** extend `api-client.ts` + `queries.ts` with research endpoints + hooks
  (`useStartResearch`, `useResearch` polling, `useResearchLibrary`,
  `useResearchSources`, `useFollowUp`, `useResearchSearch`, `useResearchStats`).
  Every fetch goes through TanStack Query (no bare `useEffect+fetch`).
- **layout/app-sidebar.tsx** add **Research** + **Library** nav (keep Dashboard/
  Upload/Files/Settings/Design); brand → "Deep Research Agent"; footer UTM update.
- **packages/shared/src/types.ts** add Research/Source/Report/Thread/Status types
  mirroring the Pydantic models.

## Standards self-check

1. S3 API default, no b2-native ✅
2. Custom user agent `b2ai-deep-research-agent-app` on the single S3 client ✅
3. Standardized `B2_*` names incl. `B2_APPLICATION_KEY_ID` + `B2_REGION` ✅
