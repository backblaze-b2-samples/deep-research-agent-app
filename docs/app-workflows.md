<!-- last_verified: 2026-06-11 -->
# App Workflows

User journeys inside the application.

## Run Research

- User navigates to `/research`
- Types a question and clicks **Research** (or Cmd/Ctrl-Enter)
- API creates the thread (status=pending) and starts a background run; the user is routed to `/research/[id]`
- The page polls every 2s: `RunStatus` shows how many sources have been fetched and cached on B2 so far
- The agent plans, web-searches, and reads sources; each fetched page is cached as HTML + readable Markdown + a full-page screenshot
- On completion, the rendered Markdown report appears with inline citations, and the cached sources are listed in the sidebar (each previewable via presigned URLs)
- On failure, the recorded error is shown
- See: [Research Agent](features/research-agent.md), [Source Caching on B2](features/source-cache.md), [Report Viewer](features/report-viewer.md)

## Ask a Follow-up

- On a completed report, the user types a follow-up in the follow-up box
- API loads the prior report as cached context and starts another run
- The thread flips back to running; the report updates and a new turn is recorded
- See: [Follow-up Chains](features/follow-up-chains.md)

## Browse and Search the Research Library

- User navigates to `/library`
- All past threads show as cards (question, status, source/turn counts, date)
- Typing in the search box switches to ranked results across questions, reports, and extracted source text
- Clicking a card opens the report; the trash button deletes a thread (scoped to its own `research/` prefix)
- See: [Research Library](features/research-library.md), [Search Across Research](features/research-search.md)

## Upload Files

- User navigates to `/upload`
- Drops or selects files in the dropzone
- Client validates file size (max 100MB) and type
- Progress bar shows per-file upload status
- On success: toast notification, green checkmark
- On failure: red status icon with error message
- User can clear completed uploads
- See: [File Upload](features/file-upload.md)

## Browse and Manage Files

- User navigates to `/files`
- Page loads file list from API (sorted most recent first)
- Files displayed in tree view with folders and type-specific icons
- Top-level folders auto-expand on load
- Hover a file row to see action buttons (preview / download / delete)
- **Preview**: opens dialog with image/PDF preview + metadata panel
- **Download**: fetches presigned URL, browser downloads file
- **Delete**: removes file from B2, row removed from tree, toast confirms
- Empty bucket shows "No files found" with upload prompt
- See: [File Browser](features/file-browser.md)

## View Dashboard

- User navigates to `/` (home)
- Two parallel API calls load: research stats and recent research
- Stats cards show: research threads, sources cached, screenshots, storage on B2
- Recent research list shows the latest threads with status, source count, and date
- Empty state: "No research yet" with a pointer to the Research page
- See: [Dashboard](features/dashboard.md)
