"""Pydantic models for the research agent.

These mirror the TypeScript types in `packages/shared/src/types.ts`. Keep the
two in sync — the frontend depends on these shapes.

Status is *derived from B2 object existence* (no database): a research's
`report.json` carries a `status` field, and the presence of `report.md`
confirms a completed report. See `docs/RELIABILITY.md`.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

ResearchStatus = Literal["pending", "running", "complete", "failed"]


class Source(BaseModel):
    """A web page the agent fetched, read, and cached on B2."""

    source_id: str
    url: str
    title: str
    fetched_at: datetime
    sha256: str
    html_bytes: int
    text_bytes: int
    # Whether a full-page screenshot was captured (a single page failing to
    # screenshot never kills the run — see RELIABILITY.md).
    has_screenshot: bool = False


class ResearchTurn(BaseModel):
    """One turn in a follow-up chain: a question and the report it produced."""

    question: str
    report_id: str
    source_ids: list[str] = []
    created_at: datetime


class ReportMeta(BaseModel):
    """`report.json` — the metadata document for a research thread."""

    research_id: str
    question: str
    model: str
    status: ResearchStatus
    created_at: datetime
    updated_at: datetime
    sources: list[Source] = []
    turns: list[ResearchTurn] = []
    # Populated only when status == "failed".
    error: str | None = None


class ResearchSummary(BaseModel):
    """Lightweight listing row for the Research Library / recent-research."""

    research_id: str
    question: str
    status: ResearchStatus
    model: str
    created_at: datetime
    updated_at: datetime
    source_count: int
    turn_count: int


class ResearchTurnView(BaseModel):
    """One turn of the conversation, paired with the report it produced.

    Unlike ``ResearchTurn`` (the metadata stored in ``report.json``), this
    carries the turn's rendered Markdown so the detail view can show the whole
    multi-turn conversation, not just the latest report. ``report_markdown`` is
    None for legacy turns whose per-turn report was never persisted.
    """

    question: str
    report_id: str
    report_markdown: str | None = None
    source_ids: list[str] = []
    created_at: datetime


class ResearchDetail(BaseModel):
    """Full research view: metadata + the conversation, turn by turn."""

    meta: ReportMeta
    # The latest long-form report (Markdown). None until the run completes.
    report_markdown: str | None = None
    # The full conversation: every completed turn with its own report, oldest
    # first. The detail page renders this so prior questions and answers stay
    # visible across follow-ups.
    turns: list[ResearchTurnView] = []


class StartResearchRequest(BaseModel):
    question: str


class StartResearchResponse(BaseModel):
    research_id: str
    status: ResearchStatus


class ResearchSearchHit(BaseModel):
    """A search match — which research, where the term was found, a snippet."""

    research_id: str
    question: str
    status: ResearchStatus
    created_at: datetime
    # Where the match landed: "question" | "report" | "source"
    matched_in: str
    snippet: str


class ResearchStats(BaseModel):
    total_research: int
    total_sources: int
    total_screenshots: int
    total_storage_bytes: int
    total_storage_human: str
    research_today: int
