"""Research Library service — list, inspect, delete past research threads.

The Library is the sample-specific *scoped* asset explorer: it browses only the
``research/`` prefix on B2 (past reports and each report's cached sources /
screenshots), as opposed to the full-bucket ``/files`` explorer kept from the
starter kit.
"""

import logging
import re
from datetime import UTC, datetime

from app.repo import b2_research as b2
from app.types import (
    ReportMeta,
    ResearchStats,
    ResearchSummary,
)
from app.types.formatting import humanize_bytes

logger = logging.getLogger(__name__)

_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class ResearchNotFoundError(Exception):
    """Raised when a research_id has no report.json on B2."""


def validate_research_id(research_id: str) -> None:
    if not research_id or not _ID_RE.match(research_id):
        raise ValueError("Invalid research id")


def _load_meta(research_id: str) -> ReportMeta:
    data = b2.get_json(b2.research_key(research_id, "report.json"))
    if data is None:
        raise ResearchNotFoundError(research_id)
    return ReportMeta(**data)


def _summary(meta: ReportMeta) -> ResearchSummary:
    return ResearchSummary(
        research_id=meta.research_id,
        question=meta.question,
        status=meta.status,
        model=meta.model,
        created_at=meta.created_at,
        updated_at=meta.updated_at,
        source_count=len(meta.sources),
        turn_count=len(meta.turns),
    )


def list_research(limit: int = 100) -> list[ResearchSummary]:
    """Return every research thread, newest-first."""
    summaries: list[ResearchSummary] = []
    for research_id in b2.list_research_ids():
        data = b2.get_json(b2.research_key(research_id, "report.json"))
        if data is None:
            continue
        summaries.append(_summary(ReportMeta(**data)))
    summaries.sort(key=lambda s: s.created_at, reverse=True)
    return summaries[:limit]


def get_meta(research_id: str) -> ReportMeta:
    validate_research_id(research_id)
    return _load_meta(research_id)


def delete_research(research_id: str) -> int:
    """Delete a thread — scoped strictly to its own ``research/<id>/`` prefix."""
    validate_research_id(research_id)
    _load_meta(research_id)  # 404 if it doesn't exist
    count = b2.delete_research(research_id)
    logger.info("Research deleted: id=%s objects=%d", research_id, count)
    return count


def get_stats() -> ResearchStats:
    """Aggregate dashboard metrics over the ``research/`` prefix."""
    contents = b2.list_keys()
    total_storage = sum(obj["Size"] for obj in contents)
    screenshots = sum(1 for obj in contents if obj["Key"].endswith("screenshot.png"))
    research_ids = b2.list_research_ids()

    today = datetime.now(UTC).date()
    research_today = 0
    total_sources = 0
    for research_id in research_ids:
        data = b2.get_json(b2.research_key(research_id, "report.json"))
        if data is None:
            continue
        total_sources += len(data.get("sources", []))
        created = data.get("created_at")
        if created:
            try:
                if datetime.fromisoformat(str(created)).date() == today:
                    research_today += 1
            except ValueError:
                pass

    return ResearchStats(
        total_research=len(research_ids),
        total_sources=total_sources,
        total_screenshots=screenshots,
        total_storage_bytes=total_storage,
        total_storage_human=humanize_bytes(total_storage),
        research_today=research_today,
    )
