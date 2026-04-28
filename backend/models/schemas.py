"""
schemas.py — Pydantic request/response models for the Research Pipeline API.

All models use Pydantic v2 syntax.
"""

from typing import Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class StartResearchRequest(BaseModel):
    """Body for POST /api/research/start"""
    topic: str = Field(..., description="Research topic to search for", min_length=3)
    max_papers: int = Field(10, description="Max papers to fetch per source", ge=1, le=50)


class AnalyseRequest(BaseModel):
    """Body for POST /api/research/analyse"""
    topic: str = Field(..., description="Research topic")
    papers: list[dict[str, Any]] = Field(..., description="List of normalised paper dicts")


class SynthesiseRequest(BaseModel):
    """Body for POST /api/research/synthesise"""
    topic: str = Field(..., description="Research topic")
    papers: list[dict[str, Any]] = Field(..., description="List of normalised paper dicts")
    findings: dict[str, Any] = Field(..., description="Output from /analyse (findings)")
    gaps: dict[str, Any] = Field(..., description="Output from /analyse (gaps)")


# ---------------------------------------------------------------------------
# Response bodies
# ---------------------------------------------------------------------------

class PaperItem(BaseModel):
    """A single normalised paper in API responses."""
    id: str = Field("", description="Best available unique identifier")
    title: str
    authors: str
    abstract: str
    year: int | None = None
    source: str = Field("unknown", description="'arxiv' or 'semantic_scholar'")
    url: str = ""
    pdf_url: str = ""
    citation_count: int = 0


class SourceBreakdown(BaseModel):
    """Paper counts per source."""
    arxiv: int = 0
    semantic_scholar: int = 0


class StartResearchResponse(BaseModel):
    """Response for POST /api/research/start"""
    papers: list[dict[str, Any]]
    total: int
    sources: SourceBreakdown


class AnalyseResponse(BaseModel):
    """Response for POST /api/research/analyse"""
    themes: list[str]
    findings: dict[str, Any]
    gaps: dict[str, Any]


class SynthesiseResponse(BaseModel):
    """Response for POST /api/research/synthesise"""
    review_markdown: str
    saved_filepath: str
    filename: str


class ReviewSummary(BaseModel):
    """Summary entry for the review history list."""
    topic: str
    saved_at: str
    filepath: str
    filename: str


class HistoryResponse(BaseModel):
    """Response for GET /api/research/history"""
    reviews: list[ReviewSummary]


class ErrorResponse(BaseModel):
    """Standard error envelope."""
    detail: str
