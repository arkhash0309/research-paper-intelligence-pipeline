"""
arxiv_tool.py — Tool for searching and fetching papers from the arXiv API.

Uses the public arXiv Atom/RSS API (no API key required).
Endpoint: https://export.arxiv.org/api/query
"""

import re

import httpx
import feedparser
from typing import Any

ARXIV_API_URL = "https://export.arxiv.org/api/query"


def _build_search_query(query: str, operator: str = "AND") -> str:
    """
    Build an arXiv search_query string from free text.

    "transformer attention mechanisms" becomes
    "all:transformer AND all:attention AND all:mechanisms". A bare
    "all:transformer attention mechanisms" only scopes the first term to the
    all: field, which gives poor relevance. Characters that have meaning in
    arXiv query syntax (quotes, parentheses, colons) are stripped.
    """
    terms = re.findall(r"[\w\-]+", query)
    if not terms:
        return f"all:{query.strip()}"
    return f" {operator} ".join(f"all:{term}" for term in terms)


async def _query_arxiv(params: dict[str, Any], error_context: str) -> str:
    """GET the arXiv API and return the Atom XML body, raising RuntimeError on failure."""
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(ARXIV_API_URL, params=params)
            response.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"arXiv API returned HTTP {e.response.status_code}") from e
    except httpx.RequestError as e:
        raise RuntimeError(f"Network error {error_context}: {e}") from e
    return response.text


async def search_arxiv(query: str, max_results: int = 10) -> list[dict[str, Any]]:
    """
    Search arXiv for papers matching the given query string.

    Args:
        query: The search query (e.g. "transformer attention mechanisms").
        max_results: Maximum number of results to return (default 10).

    Returns:
        A list of paper dicts with keys:
        title, authors, abstract, arxiv_id, pdf_url, published_date.

    Raises:
        RuntimeError: If the arXiv API call fails.
    """
    params = {
        "search_query": _build_search_query(query, "AND"),
        "start": 0,
        "max_results": max_results,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }

    # feedparser handles Atom XML parsing
    feed = feedparser.parse(await _query_arxiv(params, "contacting arXiv API"))

    # Requiring every term can be too strict for long natural-language topics;
    # fall back to matching any term (still relevance-ranked) if nothing matched.
    if not feed.entries and len(query.split()) > 1:
        params["search_query"] = _build_search_query(query, "OR")
        feed = feedparser.parse(await _query_arxiv(params, "contacting arXiv API"))

    papers: list[dict[str, Any]] = []
    for entry in feed.entries:
        # Extract arXiv ID from the entry id URL (e.g. http://arxiv.org/abs/2301.00001v1)
        arxiv_id = entry.get("id", "").split("/abs/")[-1]

        # Collect author names into a comma-separated string
        authors = ", ".join(
            author.get("name", "Unknown") for author in entry.get("authors", [])
        )

        # Find the PDF link from the list of links
        pdf_url = ""
        for link in entry.get("links", []):
            if link.get("type") == "application/pdf":
                pdf_url = link.get("href", "")
                break
        # Fallback: construct PDF URL from arxiv_id
        if not pdf_url and arxiv_id:
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"

        papers.append(
            {
                "title": entry.get("title", "").replace("\n", " ").strip(),
                "authors": authors,
                "abstract": entry.get("summary", "").replace("\n", " ").strip(),
                "arxiv_id": arxiv_id,
                "pdf_url": pdf_url,
                "published_date": entry.get("published", ""),
                "source": "arxiv",
            }
        )

    return papers


async def fetch_paper_details(arxiv_id: str) -> dict[str, Any]:
    """
    Fetch full metadata for a specific arXiv paper by its ID.

    Args:
        arxiv_id: The arXiv paper identifier (e.g. "2301.00001" or "2301.00001v2").

    Returns:
        A dict with full paper metadata including abstract and PDF link.

    Raises:
        RuntimeError: If the paper cannot be fetched or is not found.
    """
    params = {
        "id_list": arxiv_id,
        "max_results": 1,
    }

    feed = feedparser.parse(await _query_arxiv(params, f"fetching paper {arxiv_id}"))

    if not feed.entries:
        raise RuntimeError(f"No paper found for arXiv ID: {arxiv_id}")

    entry = feed.entries[0]
    authors = ", ".join(
        author.get("name", "Unknown") for author in entry.get("authors", [])
    )

    pdf_url = ""
    for link in entry.get("links", []):
        if link.get("type") == "application/pdf":
            pdf_url = link.get("href", "")
            break
    if not pdf_url:
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"

    return {
        "title": entry.get("title", "").replace("\n", " ").strip(),
        "authors": authors,
        "abstract": entry.get("summary", "").replace("\n", " ").strip(),
        "arxiv_id": arxiv_id,
        "pdf_url": pdf_url,
        "published_date": entry.get("published", ""),
        "categories": [tag.get("term", "") for tag in entry.get("tags", [])],
        "source": "arxiv",
    }
