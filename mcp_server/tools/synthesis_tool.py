"""
synthesis_tool.py — Tools that call the OpenAI API to extract insights and synthesise reviews.

The model defaults to gpt-5.4 and can be overridden with the OPENAI_MODEL
environment variable. API key is read from the OPENAI_API_KEY environment variable.
"""

import os
import json
import re
from typing import Any

from openai import OpenAI, APIError

DEFAULT_MODEL = "gpt-5.4"


def _get_client() -> OpenAI:
    """
    Build and return an OpenAI client using the key from the environment.

    Raises:
        RuntimeError: If OPENAI_API_KEY is not set.
    """
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY environment variable is not set. "
            "Copy mcp_server/.env.example to mcp_server/.env and fill in your key."
        )
    return OpenAI(api_key=api_key)


def _get_model() -> str:
    """Return the chat model to use (overridable via OPENAI_MODEL)."""
    return os.environ.get("OPENAI_MODEL", "").strip() or DEFAULT_MODEL


def _chat(prompt: str, max_completion_tokens: int, json_mode: bool, step: str) -> str:
    """
    Send a single-turn chat completion and return the text content.

    Uses ``max_completion_tokens`` (GPT-5 family and reasoning models reject
    the legacy ``max_tokens`` parameter). Reasoning tokens count against this
    budget, so callers pass generous limits.

    Raises:
        RuntimeError: On API errors, empty content, or a truncated response.
    """
    client = _get_client()
    kwargs: dict[str, Any] = {
        "model": _get_model(),
        "max_completion_tokens": max_completion_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    try:
        response = client.chat.completions.create(**kwargs)
    except APIError as e:
        raise RuntimeError(f"OpenAI API error in {step}: {e}") from e

    choice = response.choices[0]
    content = (choice.message.content or "").strip()
    if choice.finish_reason == "length":
        raise RuntimeError(
            f"OpenAI response for {step} was cut off at the token limit "
            f"({max_completion_tokens}). Try fewer papers."
        )
    if not content:
        raise RuntimeError(f"OpenAI returned an empty response for {step}.")
    return content


def _parse_json_object(raw_text: str, step: str) -> dict[str, Any]:
    """Parse a JSON object from model output, tolerating stray Markdown fences."""
    text = raw_text.strip()
    if text.startswith("```"):
        # Drop the opening fence (and optional language tag) and the closing fence
        text = text.split("\n", 1)[1] if "\n" in text else ""
        text = text.rsplit("```", 1)[0]
    try:
        result = json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Model returned non-JSON response for {step}: {e}") from e
    if not isinstance(result, dict):
        raise RuntimeError(f"Model returned JSON that is not an object for {step}.")
    return result


def _string_list(value: Any) -> list[str]:
    """Coerce a model-provided value into a list of non-empty strings."""
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def extract_key_findings(
    papers: list[dict[str, Any]], topic: str
) -> dict[str, Any]:
    """
    Use the OpenAI model to extract key themes, per-paper findings, and methodologies.

    Args:
        papers: List of normalised paper dicts (must have title, abstract, year).
        topic: The overarching research topic the user queried for.

    Returns:
        A dict with keys:
            themes          — list[str]: 3–5 main cross-paper themes
            findings_per_paper — list[dict]: {title, finding} per paper
            methodologies   — list[str]: research methods observed across papers
    """
    # Build a condensed paper list for the prompt to stay within token limits
    paper_summaries = "\n\n".join(
        f"[{i + 1}] **{p.get('title', 'Untitled')}** "
        f"({p.get('year') or 'n.d.'})\n"
        f"Authors: {p.get('authors') or 'Unknown'}\n"
        f"Abstract: {(p.get('abstract') or 'No abstract available.')[:600]}"
        for i, p in enumerate(papers)
    )

    prompt = f"""You are an expert research analyst. I will give you a list of academic papers on the topic: "{topic}".

Your task is to analyse these papers and return a structured JSON object with exactly these keys:
- "themes": an array of 3 to 5 strings, each describing a major theme that appears across multiple papers
- "findings_per_paper": an array of objects, each with "title" (string) and "finding" (string, one concise sentence summarising the key contribution)
- "methodologies": an array of strings listing distinct research methodologies used across the papers

Return ONLY valid JSON — no markdown fences, no explanation text.

Papers:
{paper_summaries}"""

    raw_text = _chat(prompt, max_completion_tokens=16000, json_mode=True, step="extract_key_findings")
    result = _parse_json_object(raw_text, "extract_key_findings")

    findings_per_paper: list[dict[str, str]] = []
    for item in result.get("findings_per_paper") or []:
        if isinstance(item, dict):
            findings_per_paper.append(
                {"title": str(item.get("title", "")), "finding": str(item.get("finding", ""))}
            )

    return {
        "themes": _string_list(result.get("themes")),
        "findings_per_paper": findings_per_paper,
        "methodologies": _string_list(result.get("methodologies")),
    }


def identify_research_gaps(
    themes: list[str], findings: list[str]
) -> dict[str, Any]:
    """
    Use the OpenAI model to identify research gaps, open questions, and debates.

    Args:
        themes: List of theme strings extracted from extract_key_findings.
        findings: List of per-paper finding strings.

    Returns:
        A dict with keys:
            gaps            — list[str]: understudied or under-explored areas
            open_questions  — list[str]: unanswered research questions
            debates         — list[str]: contradictions or active debates in the literature
    """
    themes_text = "\n".join(f"- {t}" for t in themes)
    findings_text = "\n".join(f"- {f}" for f in findings)

    prompt = f"""You are a senior research scientist performing a critical literature analysis.

Given the following themes and findings from a set of academic papers, identify the gaps and open problems in the research landscape.

**Themes:**
{themes_text}

**Key Findings:**
{findings_text}

Return a JSON object with exactly these keys:
- "gaps": array of strings describing understudied or under-explored areas
- "open_questions": array of strings listing specific unanswered research questions
- "debates": array of strings describing contradictions, conflicting results, or active debates

Return ONLY valid JSON — no markdown, no preamble."""

    raw_text = _chat(prompt, max_completion_tokens=8000, json_mode=True, step="identify_research_gaps")
    result = _parse_json_object(raw_text, "identify_research_gaps")

    return {
        "gaps": _string_list(result.get("gaps")),
        "open_questions": _string_list(result.get("open_questions")),
        "debates": _string_list(result.get("debates")),
    }


def synthesise_literature_review(
    topic: str,
    papers: list[dict[str, Any]],
    findings: dict[str, Any],
    gaps: dict[str, Any],
) -> str:
    """
    Use the OpenAI model to write a full structured literature review in Markdown format.

    Args:
        topic: The research topic string.
        papers: List of normalised paper dicts.
        findings: Output from extract_key_findings (themes, findings_per_paper, methodologies).
        gaps: Output from identify_research_gaps (gaps, open_questions, debates).

    Returns:
        A Markdown string (600–900 words) with sections:
        Introduction, Key Themes, Major Findings, Research Gaps, Conclusion,
        followed by a References section generated from ``papers``.
    """
    # Give every paper a ready-made citation key so the model cites real
    # papers in a consistent format instead of inventing authors.
    paper_refs = "\n".join(
        f"- {_citation_key(p)} — {p.get('title') or 'Untitled'}"
        for p in papers
    )

    themes_text = "\n".join(f"- {t}" for t in findings.get("themes", []))
    findings_text = "\n".join(
        f"- {fp.get('title', '')}: {fp.get('finding', '')}"
        for fp in findings.get("findings_per_paper", [])
    )
    gaps_text = "\n".join(f"- {g}" for g in gaps.get("gaps", []))
    questions_text = "\n".join(f"- {q}" for q in gaps.get("open_questions", []))
    debates_text = "\n".join(f"- {d}" for d in gaps.get("debates", []))

    prompt = f"""You are an academic writer producing a structured literature review for the topic: "{topic}".

Write a literature review in Markdown with exactly these five sections:
1. ## Introduction
2. ## Key Themes
3. ## Major Findings
4. ## Research Gaps & Open Questions
5. ## Conclusion

Guidelines:
- Target 600–900 words total
- Cite papers inline using exactly the citation key shown before each paper below, e.g. (Vaswani et al., 2017)
- Only cite papers from the list below — never invent authors, years or papers
- Do NOT write a References or Bibliography section; it is appended automatically
- Be analytical, not just descriptive — discuss relationships between findings
- In the Research Gaps section, include both gaps and open questions

Use the following material:

**Papers (citation key — title):**
{paper_refs}

**Themes:**
{themes_text}

**Findings:**
{findings_text}

**Gaps:**
{gaps_text}

**Open Questions:**
{questions_text}

**Debates:**
{debates_text}

Write the full Markdown review now:"""

    review = _chat(prompt, max_completion_tokens=16000, json_mode=False, step="synthesise_literature_review")
    # Drop any references list the model wrote anyway, then append the real one
    review = re.split(r"\n#{1,6}\s*(?:References|Bibliography)\b", review, flags=re.IGNORECASE)[0]
    return f"{review.rstrip()}\n\n{_references_section(papers)}\n"


def _author_list(paper: dict[str, Any]) -> list[str]:
    """Split the comma-separated authors string into individual names."""
    return [a.strip() for a in str(paper.get("authors") or "").split(",") if a.strip()]


def _citation_key(paper: dict[str, Any]) -> str:
    """Build an author-year citation key such as "(Vaswani et al., 2017)"."""
    authors = _author_list(paper)
    year = paper.get("year") or "n.d."
    if not authors:
        short_title = " ".join(str(paper.get("title") or "Untitled").split()[:4])
        return f"({short_title}, {year})"
    surname = authors[0].split()[-1]
    if len(authors) == 1:
        return f"({surname}, {year})"
    if len(authors) == 2:
        return f"({surname} & {authors[1].split()[-1]}, {year})"
    return f"({surname} et al., {year})"


def _references_section(papers: list[dict[str, Any]]) -> str:
    """Build a Markdown References section from the actual input papers."""
    entries: list[str] = []
    def sort_key(paper: dict[str, Any]) -> str:
        authors = _author_list(paper)
        return (authors[0].split()[-1] if authors else str(paper.get("title") or "")).lower()

    for paper in sorted(papers, key=sort_key):
        authors = _author_list(paper)
        author_text = ", ".join(authors[:6]) + (", et al." if len(authors) > 6 else "")
        title = str(paper.get("title") or "Untitled")
        url = paper.get("url") or paper.get("pdf_url")
        title_text = f"[{title}]({url})" if url else title
        entries.append(
            f"- {author_text or 'Unknown authors'} ({paper.get('year') or 'n.d.'}). {title_text}."
        )
    return "## References\n\n" + "\n".join(entries)
