"""
research.py — FastAPI router for all /api/research endpoints.

Endpoint summary:
    POST /api/research/start      — search arXiv + Semantic Scholar, deduplicate
    POST /api/research/analyse    — extract findings and identify gaps via OpenAI
    POST /api/research/synthesise — generate and save a literature review via OpenAI
    GET  /api/research/history    — list all saved reviews
    GET  /api/research/review/{filename} — fetch a specific saved review
"""

import asyncio
import re
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
    1. Call tool_search_arxiv and tool_search_semantic_scholar concurrently.
    2. Normalise both result sets into a common schema.
    3. Deduplicate by normalised title.
    5. Return the combined, deduplicated list with source breakdown.

    Raises:
        HTTPException 502: If both search calls fail. If only one fails, its
            error is returned in ``warnings`` alongside the other source's papers.
    """
    # Run both searches concurrently; one source failing (e.g. a Semantic
    # Scholar 429) should not sink the whole run.
    arxiv_result, ss_result = await asyncio.gather(
        call_tool("tool_search_arxiv", {"query": body.topic, "max_results": body.max_papers}),
        call_tool(
            "tool_search_semantic_scholar",
            {"query": body.topic, "max_results": body.max_papers},
        ),
        return_exceptions=True,
    )

    failures: list[str] = []
    raw_results: list[list[dict[str, Any]]] = []
    for label, result in (("arXiv", arxiv_result), ("Semantic Scholar", ss_result)):
        if isinstance(result, BaseException):
            if not isinstance(result, Exception):
                raise result  # e.g. CancelledError — don't swallow it
            failures.append(f"{label}: {result}")
            raw_results.append([])
        else:
            raw_results.append(result if isinstance(result, list) else [])

    if len(failures) == 2:
        raise HTTPException(
            status_code=502,
            detail="Both paper searches failed. " + " | ".join(failures),
        )

    warnings = [
        f"Search failed for {failure} — showing results from the other source only."
        for failure in failures
    ]

    all_papers = _normalise_and_deduplicate(raw_results[0], raw_results[1])

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
        warnings=warnings,
    )


def _clean_text(value: Any) -> str:
    """Return value as a single-line string with collapsed whitespace ('' for None)."""
    if value is None:
        return ""
    return " ".join(str(value).split())


def _to_int(value: Any) -> int | None:
    """Best-effort int conversion that returns None instead of raising."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalise_paper(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Normalise a raw paper dict from arXiv or Semantic Scholar into a common schema.

    Produces a dict with keys: id, title, authors, abstract, year, source,
    url, pdf_url, citation_count. Null or missing fields from the upstream
    APIs are replaced with safe defaults.

    Args:
        raw: Raw paper dict from one of the search tools.

    Returns:
        Normalised paper dict.
    """
    source = raw.get("source") or "unknown"

    if source == "arxiv":
        paper_id = _clean_text(raw.get("arxiv_id"))
        url = f"https://arxiv.org/abs/{paper_id}" if paper_id else ""
        year = _to_int(_clean_text(raw.get("published_date"))[:4])
    else:
        paper_id = _clean_text(raw.get("paper_id"))
        url = _clean_text(raw.get("url"))
        year = _to_int(raw.get("year"))

    return {
        "id": paper_id,
        "title": _clean_text(raw.get("title")),
        "authors": _clean_text(raw.get("authors")),
        "abstract": _clean_text(raw.get("abstract")),
        "year": year,
        "source": source,
        "url": url,
        "pdf_url": _clean_text(raw.get("pdf_url")),
        "citation_count": _to_int(raw.get("citation_count")) or 0,
    }


def _title_key(title: str) -> str:
    """
    Build a comparison key for duplicate detection.

    Lowercases and strips punctuation/whitespace differences so that e.g.
    "Attention Is All You Need" and "Attention is all you need." match.
    """
    return " ".join(re.sub(r"[^a-z0-9]+", " ", title.lower()).split())


def _normalise_and_deduplicate(
    arxiv_papers: list[dict[str, Any]],
    ss_papers: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Merge two raw paper lists, normalise each entry, and deduplicate by title.

    arXiv entries are preferred over Semantic Scholar duplicates because they
    carry PDF links; the Semantic Scholar citation count is kept when merging.

    Args:
        arxiv_papers: Raw dicts from tool_search_arxiv.
        ss_papers: Raw dicts from tool_search_semantic_scholar.

    Returns:
        Deduplicated, normalised list of paper dicts.
    """
    normalised = [
        _normalise_paper(paper)
        for paper in [*arxiv_papers, *ss_papers]
        if isinstance(paper, dict)
    ]

    seen: dict[str, dict[str, Any]] = {}
    for paper in normalised:
        key = _title_key(paper["title"])
        if not key:
            continue  # Skip papers with no usable title
        existing = seen.get(key)
        if existing is None:
            seen[key] = paper
            continue

        # Keep the arXiv record, but carry over the richer metadata from the duplicate
        preferred, other = (
            (paper, existing)
            if existing["source"] != "arxiv" and paper["source"] == "arxiv"
            else (existing, paper)
        )
        preferred["citation_count"] = max(preferred["citation_count"], other["citation_count"])
        preferred["abstract"] = preferred["abstract"] or other["abstract"]
        preferred["year"] = preferred["year"] or other["year"]
        seen[key] = preferred

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
        HTTPException 502: If either OpenAI call fails.
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
        HTTPException 502: If the OpenAI call or file save fails.
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
