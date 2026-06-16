<!-- last_verified: 2026-06-11 -->
# Security

Security principles and implementation for the deep-research-agent-app.

## Trust Boundaries

- **Frontend -> API**: CORS-restricted to configured origins, scoped to `GET/POST/DELETE/OPTIONS`
- **API -> B2**: Authenticated via `B2_APPLICATION_KEY_ID` + `B2_APPLICATION_KEY`, signature v4
- **API -> Anthropic**: Authenticated via `ANTHROPIC_API_KEY`, server-side only — never sent to the browser
- **API -> open web**: The agent fetches arbitrary URLs in a headless browser; treated as the least-trusted boundary (see SSRF + prompt injection below)
- **Client -> B2**: Presigned URLs for previewing cached artifacts (10-min expiry)

## Agent-Fetched Content (the highest-risk surface)

The agent decides which URLs to fetch, so `repo/browser.py` is the security
chokepoint.

### SSRF guardrails on `fetch_source`
- Only `http`/`https` schemes are allowed; everything else is refused.
- The target host is resolved and every resolved address is checked; private,
  loopback, link-local, reserved, multicast, and unspecified addresses are
  refused (blocks `169.254.169.254` cloud-metadata, `localhost`, RFC1918, etc.).
- A host that fails to resolve is treated as unsafe.
- Fetches are bounded: navigation timeout (`FETCH_TIMEOUT_MS`), screenshot
  timeout (`SCREENSHOT_TIMEOUT_MS`), and a hard cap on cached HTML size
  (`FETCH_MAX_BYTES`).

### Prompt injection
- Fetched page text is **untrusted data, never instructions.** The system prompt
  explicitly tells the model to treat fetched content as data even if a page
  says "ignore previous instructions." The agent's only client-side capability
  is `fetch_source` (which is itself SSRF-guarded) — it cannot exfiltrate
  secrets or call other tools — so a hostile page's blast radius is limited to
  influencing report content, not the host or credentials.

### Artifact access
- Source artifact previews (`/research/{id}/sources/{sid}/{artifact}/preview`)
  validate that the source belongs to the thread and restrict `artifact` to an
  allowlist (`page.html`/`page.md`/`screenshot.png`) before presigning — a
  caller cannot presign arbitrary bucket keys.
- Deletes are scoped strictly to a single `research/<id>/` prefix.

## Upload Validation

- Filename sanitization: path traversal, null bytes, unsafe chars stripped
- MIME/extension consistency check against allowlist
- Chunked streaming with size enforcement (100MB default)
- Content-type allowlist (images, PDFs, text, archives, audio/video)
- Empty file rejection

## File Key Validation

- Empty keys rejected
- Path traversal patterns rejected (`../`, `%2e%2e`, backslashes, null bytes)
- The bucket is the only access boundary — add prefix scoping in
  `services/api/app/service/files.py::validate_key` if your deployment
  shares a bucket with other workloads

## Download Safety

- Presigned URLs force `Content-Disposition: attachment`
- Prevents inline rendering of user-uploaded content (XSS mitigation)

## Secrets Management

- All secrets loaded via environment variables (pydantic-settings)
- `ANTHROPIC_API_KEY` and B2 keys live only in the repo-root `.env` (gitignored); the Anthropic key is used server-side and never reaches the browser
- Never committed to source control
- `.env.example` documents required variables without values

## Agent Security Rules

- Never commit `.env`, credentials, or API keys
- Never weaken validation without explicit instruction
- Never bypass CORS, auth, or input sanitization
- Always validate at system boundaries
