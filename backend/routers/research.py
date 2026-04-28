"""
research.py — FastAPI router for all /api/research endpoints.

Endpoint summary:
    POST /api/research/start      — search arXiv + Semantic Scholar, deduplicate
    POST /api/research/analyse    — extract findings and identify gaps via Claude
    POST /api/research/synthesise — generate and save a literature review via Claude
    GET  /api/research/history    — list all saved reviews
    GET  /api/research/review/{filename} — fetch a specific saved review
"""

from typing import Any

from fastapi import APIRouter, HTTPException

from models.schemas import (
    StartResearchRequest,
    StartResearchResponse,
    SourceBreakdown,
    AnalyseRequest,
    AnalyseResponse,
    SynthesiseRequest,
    SynthesiseResponse,
    HistoryResponse,
    ReviewSummary,
)
from services.mcp_client import call_tool

router = APIRouter(prefix="/api/research", tags=["research"])


# ---------------------------------------------------------------------------
# POST /api/research/start
# ---------------------------------------------------------------------------
@router.post("/start", response_model=StartResearchResponse)
async def start_research(body: StartResearchRequest) -> StartResearchResponse:
    """
    Search arXiv and Semantic Scholar for papers on the given topic.

    Steps:
    1. Call tool_search_arxiv to fetch papers from arXiv.
    2. Call tool_search_semantic_scholar to fetch papers from Semantic Scholar.
    3. Normalise both result sets using parse_paper (via the MCP paper_parser tool).
    4. Deduplicate by title similarity.
    5. Return the combined, deduplicated list with source breakdown.

    Raises:
        HTTPException 502: If either search call fails.
    """
    # Run both searches — errors are surfaced as HTTPException
    try:
        arxiv_papers: list[dict[str, Any]] = await call_tool(
            "tool_search_arxiv",
            {"query": body.topic, "max_results": body.max_papers},
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=f"arXiv search failed: {e}")

    try:
        ss_papers: list[dict[str, Any]] = await call_tool(
            "tool_search_semantic_scholar",
            {"query": body.topic, "max_results": body.max_papers},
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=f"Semantic Scholar search failed: {e}")

    # Normalise and deduplicate inline (avoids an extra MCP round-trip for a simple operation)
    all_papers = _normalise_and_deduplicate(arxiv_papers or [], ss_papers or [])

    sources = SourceBreakdown(
        arxiv=sum(1 for p in all_papers if p.get("source") == "arxiv"),
        semantic_scholar=sum(
            1 for p in all_papers if p.get("source") == "semantic_scholar"
        ),
    )

    return StartResearchResponse(
        papers=all_papers,
        total=len(all_papers),
        sources=sources,
    )


def _normalise_paper(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Normalise a raw paper dict from arXiv or Semantic Scholar into a common schema.

    Produces a dict with keys: id, title, authors, abstract, year, source,
    url, pdf_url, citation_count.

    Args:
        raw: Raw paper dict from one of the search tools.

    Returns:
        Normalised paper dict.
    """
    source = raw.get("source", "unknown")

    if source == "arxiv":
        paper_id = raw.get("arxiv_id", "")
        url = f"https://arxiv.org/abs/{paper_id}" if paper_id else ""
        pdf_url = raw.get("pdf_url", "")
        published_date = raw.get("published_date", "")
        year: int | None = int(published_date[:4]) if len(published_date) >= 4 else None
        citation_count = raw.get("citation_count", 0)
    else:
        paper_id = raw.get("paper_id", "")
        url = raw.get("url", "")
        pdf_url = raw.get("pdf_url", "")
        year = raw.get("year")
        citation_count = raw.get("citation_count", 0)

    return {
        "id": paper_id,
        "title": raw.get("title", "").strip(),
        "authors": raw.get("authors", ""),
        "abstract": raw.get("abstract", "").strip(),
        "year": year,
        "source": source,
        "url": url,
        "pdf_url": pdf_url,
        "citation_count": citation_count,
    }


def _normalise_and_deduplicate(
    arxiv_papers: list[dict[str, Any]],
    ss_papers: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Merge two raw paper lists, normalise each entry, and deduplicate by title.

    arXiv entries are preferred over Semantic Scholar duplicates because they
    carry PDF links.

    Args:
        arxiv_papers: Raw dicts from tool_search_arxiv.
        ss_papers: Raw dicts from tool_search_semantic_scholar.

    Returns:
        Deduplicated, normalised list of paper dicts.
    """
    # _normalise_paper is defined below in this module

    normalised: list[dict[str, Any]] = []
    for paper in arxiv_papers:
        normalised.append(_normalise_paper(paper))
    for paper in ss_papers:
        normalised.append(_normalise_paper(paper))

    # Deduplicate: prefer arXiv version when title matches
    seen: dict[str, dict[str, Any]] = {}
    for paper in normalised:
        key = paper.get("title", "").lower().strip()
        if not key:
            continue
        if key not in seen:
            seen[key] = paper
        elif seen[key].get("source") != "arxiv" and paper.get("source") == "arxiv":
            seen[key] = paper

    return list(seen.values())


# ---------------------------------------------------------------------------
# POST /api/research/analyse
# ---------------------------------------------------------------------------
@router.post("/analyse", response_model=AnalyseResponse)
async def analyse_papers(body: AnalyseRequest) -> AnalyseResponse:
    """
    Extract key findings from a list of papers and identify research gaps.

    Steps:
    1. Call tool_extract_key_findings with the papers and topic.
    2. Flatten finding strings for the gaps tool.
    3. Call tool_identify_research_gaps with themes and findings.
    4. Return combined analysis.

    Raises:
        HTTPException 502: If either Claude API call fails.
    """
    try:
        findings: dict[str, Any] = await call_tool(
            "tool_extract_key_findings",
            {"papers": body.papers, "topic": body.topic},
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=f"Key findings extraction failed: {e}")

    # Flatten the per-paper findings into a list of strings for the gaps tool
    finding_strings: list[str] = [
        fp.get("finding", "") for fp in findings.get("findings_per_paper", [])
    ]

    try:
        gaps: dict[str, Any] = await call_tool(
            "tool_identify_research_gaps",
            {
                "themes": findings.get("themes", []),
                "findings": finding_strings,
            },
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=f"Research gap identification failed: {e}")

    return AnalyseResponse(
        themes=findings.get("themes", []),
        findings=findings,
        gaps=gaps,
    )


# ---------------------------------------------------------------------------
# POST /api/research/synthesise
# ---------------------------------------------------------------------------
@router.post("/synthesise", response_model=SynthesiseResponse)
async def synthesise_review(body: SynthesiseRequest) -> SynthesiseResponse:
    """
    Generate a structured literature review and save it to disk.

    Steps:
    1. Call tool_synthesise_literature_review to produce a Markdown review.
    2. Call tool_save_review to persist the review as a JSON file.
    3. Return the Markdown and the saved file path.

    Raises:
        HTTPException 502: If the Claude API call or file save fails.
    """
    try:
        review_markdown: str = await call_tool(
            "tool_synthesise_literature_review",
            {
                "topic": body.topic,
                "papers": body.papers,
                "findings": body.findings,
                "gaps": body.gaps,
            },
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=f"Literature review synthesis failed: {e}")

    # Build metadata to store alongside the review
    metadata: dict[str, Any] = {
        "paper_count": len(body.papers),
        "sources": {
            "arxiv": sum(1 for p in body.papers if p.get("source") == "arxiv"),
            "semantic_scholar": sum(
                1 for p in body.papers if p.get("source") == "semantic_scholar"
            ),
        },
        "themes": body.findings.get("themes", []),
    }

    try:
        save_result: dict[str, Any] = await call_tool(
            "tool_save_review",
            {
                "topic": body.topic,
                "review_markdown": review_markdown,
                "metadata": metadata,
            },
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=f"Failed to save review: {e}")

    return SynthesiseResponse(
        review_markdown=review_markdown,
        saved_filepath=save_result.get("filepath", ""),
        filename=save_result.get("filename", ""),
    )


# ---------------------------------------------------------------------------
# GET /api/research/history
# ---------------------------------------------------------------------------
@router.get("/history", response_model=HistoryResponse)
async def get_history() -> HistoryResponse:
    """
    List all saved literature reviews from storage/reviews/.

    Returns:
        A list of review summaries sorted by saved_at descending (newest first).
    """
    try:
        reviews_raw: list[dict[str, Any]] = await call_tool("tool_list_reviews", {})
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=f"Failed to load review history: {e}")

    reviews = [
        ReviewSummary(
            topic=r.get("topic", ""),
            saved_at=r.get("saved_at", ""),
            filepath=r.get("filepath", ""),
            filename=r.get("filename", ""),
        )
        for r in (reviews_raw or [])
    ]

    return HistoryResponse(reviews=reviews)


# ---------------------------------------------------------------------------
# GET /api/research/review/{filename}
# ---------------------------------------------------------------------------
@router.get("/review/{filename}")
async def get_review(filename: str) -> dict[str, Any]:
    """
    Fetch a specific saved review by filename.

    Args:
        filename: The JSON file name (e.g. "20240128_143022_transformers.json").

    Returns:
        Full review record dict.

    Raises:
        HTTPException 404: If the file does not exist.
        HTTPException 502: If the MCP call fails unexpectedly.
    """
    try:
        review: dict[str, Any] = await call_tool(
            "tool_load_review", {"filename": filename}
        )
    except RuntimeError as e:
        error_str = str(e)
        if "not found" in error_str.lower():
            raise HTTPException(status_code=404, detail=f"Review not found: {filename}")
        raise HTTPException(status_code=502, detail=f"Failed to load review: {e}")

    return review
