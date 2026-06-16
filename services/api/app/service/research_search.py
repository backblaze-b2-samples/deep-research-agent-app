"""Keyword/metadata search across past research (v1).

Searches each thread's question, its report Markdown, and the extracted
readable text of its cached sources for a query string. Returns ranked hits
with a short snippet showing where the match landed.

This is intentionally simple substring/keyword matching — semantic search
(Voyage embeddings, a second key) is a v2 item tracked in the tech-debt log.
"""

import logging

from app.repo import b2_research as b2
from app.types import ReportMeta, ResearchSearchHit

logger = logging.getLogger(__name__)

_SNIPPET_PAD = 90


def _snippet(text: str, needle: str) -> str:
    idx = text.lower().find(needle.lower())
    if idx == -1:
        return text[: _SNIPPET_PAD * 2].strip()
    start = max(0, idx - _SNIPPET_PAD)
    end = min(len(text), idx + len(needle) + _SNIPPET_PAD)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    return f"{prefix}{text[start:end].strip()}{suffix}"


def _hit(meta: ReportMeta, matched_in: str, snippet: str) -> ResearchSearchHit:
    return ResearchSearchHit(
        research_id=meta.research_id,
        question=meta.question,
        status=meta.status,
        created_at=meta.created_at,
        matched_in=matched_in,
        snippet=snippet,
    )


def search(query: str, limit: int = 50) -> list[ResearchSearchHit]:
    q = query.strip()
    if not q:
        return []
    ql = q.lower()
    hits: list[ResearchSearchHit] = []

    for research_id in b2.list_research_ids():
        data = b2.get_json(b2.research_key(research_id, "report.json"))
        if data is None:
            continue
        meta = ReportMeta(**data)

        # 1. Question match (highest signal).
        if ql in meta.question.lower():
            hits.append(_hit(meta, "question", _snippet(meta.question, q)))
            continue

        # 2. Report body match.
        report = b2.get_text(b2.research_key(research_id, "report.md"))
        if report and ql in report.lower():
            hits.append(_hit(meta, "report", _snippet(report, q)))
            continue

        # 3. Source title / extracted-text match.
        matched_source = False
        for source in meta.sources:
            if ql in source.title.lower():
                hits.append(_hit(meta, "source", source.title))
                matched_source = True
                break
            text = b2.get_text(
                b2.source_key(research_id, source.source_id, "page.md")
            )
            if text and ql in text.lower():
                hits.append(_hit(meta, "source", _snippet(text, q)))
                matched_source = True
                break
        if matched_source:
            continue

    hits.sort(key=lambda h: h.created_at, reverse=True)
    return hits[:limit]
