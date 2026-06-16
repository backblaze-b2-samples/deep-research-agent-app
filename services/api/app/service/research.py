"""Research agent orchestration — the manual Claude tool-use loop.

This is the core feature. ``run_research`` drives a real Claude Sonnet 4.6
agentic loop: the model plans, calls Anthropic's bundled web search, and calls
our client-side ``fetch_source`` tool. We intercept every ``fetch_source`` call
to render the page (Playwright), cache its HTML / readable text / screenshot on
B2, and feed the readable text back to the model. When the model stops
requesting tools it has written the final report, which we also persist to B2.

Status is derived from B2 object existence — ``report.json`` carries a status
field and the run is "complete" once ``report.md`` exists. No database.

The run is kicked off in a FastAPI BackgroundTask; exceptions are caught and
recorded as a ``failed`` status so the frontend poll surfaces the error.
"""

import logging
import uuid
from datetime import UTC, datetime

from app.config import settings
from app.repo import b2_research as b2
from app.repo import browser, llm_client
from app.types import ReportMeta, ResearchTurn, Source

logger = logging.getLogger(__name__)

REPORT_JSON = "report.json"
REPORT_MD = "report.md"


def _now() -> datetime:
    return datetime.now(UTC)


def _load_meta(research_id: str) -> ReportMeta | None:
    data = b2.get_json(b2.research_key(research_id, REPORT_JSON))
    return ReportMeta(**data) if data else None


def _save_meta(meta: ReportMeta) -> None:
    meta.updated_at = _now()
    b2.put_json(
        b2.research_key(meta.research_id, REPORT_JSON),
        meta.model_dump(mode="json"),
    )


def create_research(question: str) -> str:
    """Create a new research thread (status=pending) and return its id."""
    research_id = uuid.uuid4().hex[:16]
    now = _now()
    meta = ReportMeta(
        research_id=research_id,
        question=question.strip(),
        model=settings.anthropic_model,
        status="pending",
        created_at=now,
        updated_at=now,
    )
    _save_meta(meta)
    logger.info("Research created: id=%s", research_id)
    return research_id


def add_follow_up(research_id: str, question: str) -> ReportMeta:
    """Append a follow-up turn to an existing thread and mark it pending."""
    meta = _load_meta(research_id)
    if meta is None:
        raise KeyError(research_id)
    meta.status = "pending"
    meta.question = question.strip()  # latest question drives the next run
    _save_meta(meta)
    return meta


def _cache_source(research_id: str, url: str) -> tuple[Source | None, str]:
    """Execute one fetch_source call: render, cache to B2, return text.

    Returns (Source or None on failure, text to feed back to the model).
    A failure here is non-fatal — the agent gets an error string and moves on.
    """
    try:
        page = browser.fetch_page(url)
    except browser.UnsafeUrlError as e:
        return None, f"Refused to fetch (blocked URL): {e}"
    except RuntimeError as e:
        logger.warning("fetch_source failed url=%s: %s", url, e)
        return None, f"Could not load the page: {e}"

    source_id = uuid.uuid4().hex[:12]
    b2.put_bytes(b2.source_key(research_id, source_id, "page.html"), page.html, "text/html")
    b2.put_text(
        b2.source_key(research_id, source_id, "page.md"),
        page.text_markdown,
        "text/markdown",
    )
    if page.screenshot_png is not None:
        b2.put_bytes(
            b2.source_key(research_id, source_id, "screenshot.png"),
            page.screenshot_png,
            "image/png",
        )
    source = Source(
        source_id=source_id,
        url=page.url,
        title=page.title,
        fetched_at=_now(),
        sha256=page.sha256,
        html_bytes=len(page.html),
        text_bytes=len(page.text_markdown.encode("utf-8")),
        has_screenshot=page.has_screenshot,
    )
    b2.put_json(
        b2.source_key(research_id, source_id, "meta.json"),
        source.model_dump(mode="json"),
    )

    # Truncate the text handed back to the model to bound context/cost.
    text = page.text_markdown[:12_000]
    return source, (
        f"[source_id={source_id}] {page.title} ({page.url})\n\n{text}"
    )


def _initial_messages(meta: ReportMeta) -> list[dict]:
    """Build the opening conversation, loading prior reports for follow-ups."""
    messages: list[dict] = []
    prior = b2.get_text(b2.research_key(meta.research_id, REPORT_MD))
    if prior and meta.turns:
        # Follow-up: prior report becomes cached context.
        messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Here is the prior research report for this thread. "
                            "Build on it for the follow-up question.\n\n" + prior
                        ),
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
            }
        )
    messages.append({"role": "user", "content": meta.question})
    return messages


def run_research(research_id: str) -> None:
    """Drive the agentic loop to completion and persist the report to B2.

    Intended to run inside a FastAPI BackgroundTask.
    """
    meta = _load_meta(research_id)
    if meta is None:
        logger.error("run_research: unknown id=%s", research_id)
        return

    meta.status = "running"
    _save_meta(meta)

    messages = _initial_messages(meta)
    new_sources: list[Source] = []
    # The bundled web_search tool runs in a server-side code-execution
    # container. Once a turn uses it, every subsequent turn must replay that
    # container's id or the API rejects the request (400: "container_id is
    # required when there are pending tool uses generated by code execution").
    container: str | None = None

    try:
        while True:
            message = llm_client.create_turn(messages, container=container)
            container = llm_client.container_id(message) or container
            messages.append({"role": "assistant", "content": message.content})

            tool_results = []
            for tool_id, name, tool_input in llm_client.iter_tool_uses(message):
                if name != "fetch_source":
                    continue  # web_search is server-side; nothing to execute
                if len(new_sources) >= settings.research_max_sources:
                    tool_results.append(
                        _tool_result(tool_id, "Source budget reached; write the report now.")
                    )
                    continue
                source, text = _cache_source(research_id, tool_input.get("url", ""))
                if source is not None:
                    new_sources.append(source)
                    meta.sources.append(source)
                    _save_meta(meta)  # incremental — library shows progress
                tool_results.append(_tool_result(tool_id, text))

            if tool_results:
                messages.append({"role": "user", "content": tool_results})
                continue

            # No tool calls -> the assistant produced the final report.
            report_md = llm_client.extract_text(message)
            _finalize(meta, report_md, new_sources)
            return
    except Exception as e:
        logger.exception("Research run failed id=%s", research_id)
        meta.status = "failed"
        meta.error = str(e)
        _save_meta(meta)
        b2.put_text(b2.research_key(research_id, ".failed"), str(e), "text/plain")


def _tool_result(tool_use_id: str, content: str) -> dict:
    return {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": content,
    }


def _finalize(meta: ReportMeta, report_md: str, run_sources: list[Source]) -> None:
    report_id = uuid.uuid4().hex[:12]
    # report.md is the latest report (follow-up context + search); the per-turn
    # copy under reports/<report_id>.md preserves the full conversation history.
    b2.put_text(b2.research_key(meta.research_id, REPORT_MD), report_md, "text/markdown")
    b2.put_text(b2.turn_report_key(meta.research_id, report_id), report_md, "text/markdown")
    meta.turns.append(
        ResearchTurn(
            question=meta.question,
            report_id=report_id,
            source_ids=[s.source_id for s in run_sources],
            created_at=_now(),
        )
    )
    meta.status = "complete"
    meta.error = None
    _save_meta(meta)
    logger.info(
        "Research complete: id=%s sources=%d", meta.research_id, len(meta.sources)
    )
