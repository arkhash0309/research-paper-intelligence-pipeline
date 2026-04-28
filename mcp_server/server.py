"""
server.py — MCP server entry point for the Research Paper Intelligence Pipeline.

Registers all 7 tools and exposes them over stdio (standard MCP transport).
Run with:  python mcp_server/server.py

Environment variables (set in mcp_server/.env):
    ANTHROPIC_API_KEY        — required for synthesis tools
    SEMANTIC_SCHOLAR_API_KEY — optional; increases rate limits
"""

from pathlib import Path
from dotenv import load_dotenv

# Load .env from the mcp_server directory before importing any tool that reads env vars
_env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=_env_path)

from mcp.server.fastmcp import FastMCP
from tools.arxiv_tool import search_arxiv, fetch_paper_details
from tools.semantic_scholar_tool import search_semantic_scholar
from tools.paper_parser_tool import parse_paper, deduplicate_papers
from tools.synthesis_tool import (
    extract_key_findings,
    identify_research_gaps,
    synthesise_literature_review,
)
from tools.save_tool import save_review, list_reviews, load_review

# Instantiate the FastMCP server — name is used in .mcp.json registration
mcp = FastMCP("research-pipeline")


# ---------------------------------------------------------------------------
# Tool 1 — search_arxiv
# ---------------------------------------------------------------------------
@mcp.tool()
async def tool_search_arxiv(query: str, max_results: int = 10) -> list[dict]:
    """
    Search arXiv for academic papers matching a query string.

    Args:
        query: Research topic or keyword string.
        max_results: Number of results to return (default 10, max ~100).

    Returns:
        List of paper dicts: title, authors, abstract, arxiv_id, pdf_url, published_date.
    """
    return await search_arxiv(query, max_results)


# ---------------------------------------------------------------------------
# Tool 2 — search_semantic_scholar
# ---------------------------------------------------------------------------
@mcp.tool()
async def tool_search_semantic_scholar(query: str, max_results: int = 10) -> list[dict]:
    """
    Search Semantic Scholar for academic papers matching a query string.

    Args:
        query: Research topic or keyword string.
        max_results: Number of results to return (default 10, max 100).

    Returns:
        List of paper dicts: title, authors, abstract, paper_id, year, citation_count, url.
    """
    return await search_semantic_scholar(query, max_results)


# ---------------------------------------------------------------------------
# Tool 3 — fetch_paper_details
# ---------------------------------------------------------------------------
@mcp.tool()
async def tool_fetch_paper_details(arxiv_id: str) -> dict:
    """
    Fetch full metadata for a specific arXiv paper by its ID.

    Args:
        arxiv_id: The arXiv identifier, e.g. "2301.00001" or "2301.00001v2".

    Returns:
        Full paper dict including abstract, categories, and PDF link.
    """
    return await fetch_paper_details(arxiv_id)


# ---------------------------------------------------------------------------
# Tool 4 — extract_key_findings
# ---------------------------------------------------------------------------
@mcp.tool()
def tool_extract_key_findings(papers: list[dict], topic: str) -> dict:
    """
    Use Claude to extract key themes, per-paper findings, and methodologies.

    Args:
        papers: List of paper dicts (must include title, abstract, year).
        topic: The overarching research topic.

    Returns:
        Dict with keys: themes (list), findings_per_paper (list), methodologies (list).
    """
    return extract_key_findings(papers, topic)


# ---------------------------------------------------------------------------
# Tool 5 — identify_research_gaps
# ---------------------------------------------------------------------------
@mcp.tool()
def tool_identify_research_gaps(themes: list[str], findings: list[str]) -> dict:
    """
    Use Claude to identify research gaps, open questions, and debates.

    Args:
        themes: List of theme strings from extract_key_findings.
        findings: List of per-paper finding strings.

    Returns:
        Dict with keys: gaps (list), open_questions (list), debates (list).
    """
    return identify_research_gaps(themes, findings)


# ---------------------------------------------------------------------------
# Tool 6 — synthesise_literature_review
# ---------------------------------------------------------------------------
@mcp.tool()
def tool_synthesise_literature_review(
    topic: str, papers: list[dict], findings: dict, gaps: dict
) -> str:
    """
    Use Claude to write a structured literature review in Markdown (600–900 words).

    Args:
        topic: The research topic string.
        papers: List of normalised paper dicts.
        findings: Output from extract_key_findings.
        gaps: Output from identify_research_gaps.

    Returns:
        Markdown string with sections: Introduction, Key Themes, Major Findings,
        Research Gaps & Open Questions, Conclusion.
    """
    return synthesise_literature_review(topic, papers, findings, gaps)


# ---------------------------------------------------------------------------
# Tool 7 — save_review
# ---------------------------------------------------------------------------
@mcp.tool()
def tool_save_review(topic: str, review_markdown: str, metadata: dict) -> dict:
    """
    Save a completed literature review as a JSON file in storage/reviews/.

    Args:
        topic: Research topic (used to generate the filename slug).
        review_markdown: The full Markdown review text.
        metadata: Arbitrary metadata dict (e.g. paper count, sources).

    Returns:
        Dict with keys: filepath, saved_at, filename.
    """
    return save_review(topic, review_markdown, metadata)


# ---------------------------------------------------------------------------
# Bonus utility tools — list and load saved reviews
# ---------------------------------------------------------------------------
@mcp.tool()
def tool_list_reviews() -> list[dict]:
    """
    List all saved literature reviews in storage/reviews/.

    Returns:
        List of summary dicts sorted by saved_at descending (newest first).
    """
    return list_reviews()


@mcp.tool()
def tool_load_review(filename: str) -> dict:
    """
    Load a saved review by filename.

    Args:
        filename: The JSON filename, e.g. "20240128_143022_transformers.json".

    Returns:
        Full review record dict including review_markdown and metadata.
    """
    return load_review(filename)


# ---------------------------------------------------------------------------
# Entry point — run the MCP server over stdio
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    mcp.run(transport="stdio")
