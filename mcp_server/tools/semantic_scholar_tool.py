"""
semantic_scholar_tool.py — Tool for searching papers via the Semantic Scholar Graph API.

API docs: https://api.semanticscholar.org/graph/v1
Free tier: 100 requests per 5 minutes unauthenticated; pass API key header for higher limits.
"""

import os
import httpx
from typing import Any


async def search_semantic_scholar(
    query: str, max_results: int = 10
) -> list[dict[str, Any]]:
    """
    Search Semantic Scholar for papers matching the query string.

    Args:
        query: The search query string.
        max_results: Maximum number of results to return (default 10).

    Returns:
        A list of paper dicts with keys:
        title, authors, abstract, paper_id, year, citation_count, url.

    Raises:
        RuntimeError: If the API call fails or rate limit is exceeded.
    """
    base_url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": min(max_results, 100),  # API hard cap is 100
        "fields": "title,authors,abstract,year,citationCount,externalIds,url",
    }

    # Build headers — include API key if available (increases rate limits)
    headers: dict[str, str] = {"Accept": "application/json"}
    api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")
    if api_key:
        headers["x-api-key"] = api_key

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(base_url, params=params, headers=headers)

            # 429 = rate limited
            if response.status_code == 429:
                raise RuntimeError(
                    "Semantic Scholar rate limit exceeded. "
                    "Wait ~5 minutes or provide a valid SEMANTIC_SCHOLAR_API_KEY."
                )
            response.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise RuntimeError(
            f"Semantic Scholar API returned HTTP {e.response.status_code}: {e.response.text}"
        ) from e
    except httpx.RequestError as e:
        raise RuntimeError(f"Network error contacting Semantic Scholar API: {e}") from e

    data = response.json()
    raw_papers: list[dict] = data.get("data", [])

    papers: list[dict[str, Any]] = []
    for paper in raw_papers:
        # Flatten authors list to a comma-separated string
        authors = ", ".join(
            a.get("name", "Unknown") for a in paper.get("authors", [])
        )

        # Construct a direct URL if not provided
        paper_id = paper.get("paperId", "")
        url = paper.get("url") or (
            f"https://www.semanticscholar.org/paper/{paper_id}" if paper_id else ""
        )

        papers.append(
            {
                "title": paper.get("title", ""),
                "authors": authors,
                "abstract": paper.get("abstract") or "",
                "paper_id": paper_id,
                "year": paper.get("year"),
                "citation_count": paper.get("citationCount", 0),
                "url": url,
                "source": "semantic_scholar",
            }
        )

    return papers
