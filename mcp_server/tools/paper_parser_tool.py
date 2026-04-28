"""
paper_parser_tool.py — Tool for extracting structured data from raw paper metadata.

This module normalises paper dicts from different sources (arXiv, Semantic Scholar)
into a consistent schema for downstream processing.
"""

from typing import Any


def parse_paper(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Normalise a raw paper dict from any source into a consistent schema.

    The normalised schema contains:
        id          — best available unique identifier
        title       — paper title (string)
        authors     — comma-separated author names
        abstract    — paper abstract text
        year        — publication year (int or None)
        source      — originating source ('arxiv' | 'semantic_scholar' | 'unknown')
        url         — link to the paper landing page
        pdf_url     — direct PDF link (may be empty string)
        citation_count — integer citation count (0 if unavailable)

    Args:
        raw: A raw paper dict as returned by arxiv_tool or semantic_scholar_tool.

    Returns:
        A normalised paper dict.
    """
    source = raw.get("source", "unknown")

    # Determine the best unique identifier based on source
    if source == "arxiv":
        paper_id = raw.get("arxiv_id", "")
        url = f"https://arxiv.org/abs/{paper_id}" if paper_id else raw.get("url", "")
        pdf_url = raw.get("pdf_url", "")
        # Extract year from published_date (ISO 8601: "2023-01-15T00:00:00Z")
        published_date = raw.get("published_date", "")
        year: int | None = int(published_date[:4]) if len(published_date) >= 4 else None
        citation_count = raw.get("citation_count", 0)
    elif source == "semantic_scholar":
        paper_id = raw.get("paper_id", "")
        url = raw.get("url", "")
        pdf_url = raw.get("pdf_url", "")
        year = raw.get("year")
        citation_count = raw.get("citation_count", 0)
    else:
        paper_id = raw.get("id", raw.get("arxiv_id", raw.get("paper_id", "")))
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


def deduplicate_papers(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Remove duplicate papers from a combined list using title similarity.

    Two papers are considered duplicates if their lowercase, stripped titles
    are identical. When duplicates exist, prefer the arXiv version (has PDF link),
    then Semantic Scholar.

    Args:
        papers: List of normalised paper dicts.

    Returns:
        Deduplicated list with one entry per unique title.
    """
    seen_titles: dict[str, dict[str, Any]] = {}

    for paper in papers:
        # Normalise the title key for comparison
        title_key = paper.get("title", "").lower().strip()
        if not title_key:
            continue  # Skip papers with no title

        if title_key not in seen_titles:
            seen_titles[title_key] = paper
        else:
            # Prefer arXiv entries because they carry PDF links
            existing = seen_titles[title_key]
            if existing.get("source") != "arxiv" and paper.get("source") == "arxiv":
                seen_titles[title_key] = paper

    return list(seen_titles.values())
