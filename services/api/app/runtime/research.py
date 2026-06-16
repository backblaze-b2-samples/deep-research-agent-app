"""Research agent routes.

Thin handlers only — all logic lives in the service layer. The agentic run is
dispatched as a FastAPI BackgroundTask so the request returns immediately and
the frontend polls ``GET /research/{id}`` for status.
"""

import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.service import library, report, research, research_search
from app.types import (
    ResearchDetail,
    ResearchSearchHit,
    ResearchStats,
    ResearchSummary,
    Source,
    StartResearchRequest,
    StartResearchResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/research", response_model=StartResearchResponse)
async def start_research(body: StartResearchRequest, background: BackgroundTasks):
    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is required")
    if len(question) > 2000:
        raise HTTPException(status_code=400, detail="Question is too long")
    research_id = research.create_research(question)
    background.add_task(research.run_research, research_id)
    logger.info("Research started: id=%s", research_id)
    return StartResearchResponse(research_id=research_id, status="pending")


@router.post("/research/{research_id}/follow-up", response_model=StartResearchResponse)
async def follow_up(
    research_id: str, body: StartResearchRequest, background: BackgroundTasks
):
    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is required")
    try:
        library.validate_research_id(research_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    try:
        research.add_follow_up(research_id, question)
    except KeyError:
        raise HTTPException(status_code=404, detail="Research not found") from None
    background.add_task(research.run_research, research_id)
    return StartResearchResponse(research_id=research_id, status="pending")


@router.get("/research", response_model=list[ResearchSummary])
async def list_research(limit: int = 100):
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="Limit must be 1-500")
    return library.list_research(limit=limit)


@router.get("/research/stats", response_model=ResearchStats)
async def research_stats():
    return library.get_stats()


@router.get("/research/search", response_model=list[ResearchSearchHit])
async def search_research(q: str = "", limit: int = 50):
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=400, detail="Limit must be 1-200")
    return research_search.search(q, limit=limit)


@router.get("/research/{research_id}", response_model=ResearchDetail)
async def get_research(research_id: str):
    try:
        library.validate_research_id(research_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    try:
        return report.get_detail(research_id)
    except library.ResearchNotFoundError:
        raise HTTPException(status_code=404, detail="Research not found") from None


@router.get("/research/{research_id}/sources", response_model=list[Source])
async def get_sources(research_id: str):
    try:
        library.validate_research_id(research_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    try:
        return report.get_sources(research_id)
    except library.ResearchNotFoundError:
        raise HTTPException(status_code=404, detail="Research not found") from None


@router.get("/research/{research_id}/sources/{source_id}/{artifact}/preview")
async def preview_source_artifact(research_id: str, source_id: str, artifact: str):
    """Presigned URL for a cached source artifact (page.html/page.md/screenshot.png)."""
    try:
        url = report.get_source_artifact_url(research_id, source_id, artifact)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    except library.ResearchNotFoundError:
        raise HTTPException(status_code=404, detail="Artifact not found") from None
    return {"url": url}


@router.delete("/research/{research_id}")
async def delete_research(research_id: str):
    try:
        library.validate_research_id(research_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    try:
        count = library.delete_research(research_id)
    except library.ResearchNotFoundError:
        raise HTTPException(status_code=404, detail="Research not found") from None
    return {"deleted": True, "research_id": research_id, "objects": count}
