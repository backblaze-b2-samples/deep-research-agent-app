"""Report + source views for a single research thread.

Serves the rendered Markdown report, the list of cached sources, and presigned
URLs for previewing each source's cached page / screenshot from B2.
"""

import logging

from app.repo import b2_research as b2
from app.service.library import (
    ResearchNotFoundError,
    get_meta,
    validate_research_id,
)
from app.types import ReportMeta, ResearchDetail, ResearchTurnView, Source

logger = logging.getLogger(__name__)

# Which cached artifacts a caller may request a presigned URL for.
_ALLOWED_ARTIFACTS = {
    "page.html": "text/html",
    "page.md": "text/markdown",
    "screenshot.png": "image/png",
}


def get_detail(research_id: str) -> ResearchDetail:
    """Full research view: metadata + the conversation, turn by turn.

    Each completed turn is paired with its own report Markdown so the whole
    multi-turn conversation renders, not just the latest answer. Turns written
    before per-turn reports existed have no ``reports/<report_id>.md``; for the
    most recent such turn we fall back to ``report.md`` so legacy threads still
    show their latest report.
    """
    meta: ReportMeta = get_meta(research_id)
    latest_md = b2.get_text(b2.research_key(research_id, "report.md"))

    turns: list[ResearchTurnView] = []
    for i, turn in enumerate(meta.turns):
        md = b2.get_text(b2.turn_report_key(research_id, turn.report_id))
        if md is None and i == len(meta.turns) - 1:
            md = latest_md  # legacy fallback for the most recent turn
        turns.append(
            ResearchTurnView(
                question=turn.question,
                report_id=turn.report_id,
                report_markdown=md,
                source_ids=turn.source_ids,
                created_at=turn.created_at,
            )
        )

    return ResearchDetail(meta=meta, report_markdown=latest_md, turns=turns)


def get_sources(research_id: str) -> list[Source]:
    """Return the cached sources for a research thread."""
    return get_meta(research_id).sources


def get_source_artifact_url(
    research_id: str, source_id: str, artifact: str
) -> str:
    """Presigned URL for a cached source artifact (10-min expiry).

    Validates the id and artifact name, and confirms the source belongs to the
    thread, before presigning — so this can never be used to read arbitrary
    keys outside ``research/<id>/sources/<source_id>/``.
    """
    validate_research_id(research_id)
    validate_research_id(source_id)
    if artifact not in _ALLOWED_ARTIFACTS:
        raise ValueError("Unknown artifact")

    meta = get_meta(research_id)
    if not any(s.source_id == source_id for s in meta.sources):
        raise ResearchNotFoundError(source_id)

    key = b2.source_key(research_id, source_id, artifact)
    if not b2.object_exists(key):
        raise ResearchNotFoundError(key)
    return b2.presign(key)
