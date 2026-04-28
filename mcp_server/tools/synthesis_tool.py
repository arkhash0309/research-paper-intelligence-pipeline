"""
synthesis_tool.py — Tools that call the OpenAI API to extract insights and synthesise reviews.

All OpenAI calls use gpt-5.4.
API key is read from the OPENAI_API_KEY environment variable.
"""

import os
import json
from typing import Any

from openai import OpenAI, APIError


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


def extract_key_findings(
    papers: list[dict[str, Any]], topic: str
) -> dict[str, Any]:
    """
    Use GPT-5.4 to extract key themes, per-paper findings, and methodologies.

    Args:
        papers: List of normalised paper dicts (must have title, abstract, year).
        topic: The overarching research topic the user queried for.

    Returns:
        A dict with keys:
            themes          — list[str]: 3–5 main cross-paper themes
            findings_per_paper — list[dict]: {title, finding} per paper
            methodologies   — list[str]: research methods observed across papers
    """
    client = _get_client()

    # Build a condensed paper list for the prompt to stay within token limits
    paper_summaries = "\n\n".join(
        f"[{i + 1}] **{p.get('title', 'Untitled')}** "
        f"({p.get('year', 'n.d.')})\n"
        f"Authors: {p.get('authors', 'Unknown')}\n"
        f"Abstract: {p.get('abstract', 'No abstract available.')[:600]}"
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

    try:
        response = client.chat.completions.create(
            model="gpt-5.4",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = response.choices[0].message.content.strip()

        # Strip markdown code fences if the model wraps the JSON anyway
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]

        result: dict[str, Any] = json.loads(raw_text)
        return result
    except json.JSONDecodeError as e:
        raise RuntimeError(f"GPT-5.4 returned non-JSON response for extract_key_findings: {e}") from e
    except APIError as e:
        raise RuntimeError(f"OpenAI API error in extract_key_findings: {e}") from e


def identify_research_gaps(
    themes: list[str], findings: list[str]
) -> dict[str, Any]:
    """
    Use GPT-5.4 to identify research gaps, open questions, and debates.

    Args:
        themes: List of theme strings extracted from extract_key_findings.
        findings: List of per-paper finding strings.

    Returns:
        A dict with keys:
            gaps            — list[str]: understudied or under-explored areas
            open_questions  — list[str]: unanswered research questions
            debates         — list[str]: contradictions or active debates in the literature
    """
    client = _get_client()

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

    try:
        response = client.chat.completions.create(
            model="gpt-5.4",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = response.choices[0].message.content.strip()

        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]

        result: dict[str, Any] = json.loads(raw_text)
        return result
    except json.JSONDecodeError as e:
        raise RuntimeError(f"GPT-5.4 returned non-JSON response for identify_research_gaps: {e}") from e
    except APIError as e:
        raise RuntimeError(f"OpenAI API error in identify_research_gaps: {e}") from e


def synthesise_literature_review(
    topic: str,
    papers: list[dict[str, Any]],
    findings: dict[str, Any],
    gaps: dict[str, Any],
) -> str:
    """
    Use GPT-5.4 to write a full structured literature review in Markdown format.

    Args:
        topic: The research topic string.
        papers: List of normalised paper dicts.
        findings: Output from extract_key_findings (themes, findings_per_paper, methodologies).
        gaps: Output from identify_research_gaps (gaps, open_questions, debates).

    Returns:
        A Markdown string (600–900 words) with sections:
        Introduction, Key Themes, Major Findings, Research Gaps, Conclusion.
    """
    client = _get_client()

    # Summarise papers for citation reference
    paper_refs = "\n".join(
        f"- {p.get('title', 'Untitled')} ({p.get('year', 'n.d.')}) — {p.get('authors', 'Unknown')}"
        for p in papers
    )

    themes_text = "\n".join(f"- {t}" for t in findings.get("themes", []))
    findings_text = "\n".join(
        f"- {fp.get('title', '')} ({fp.get('finding', '')})"
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
- Cite papers inline by title and year, e.g. (Smith et al., 2023)
- Be analytical, not just descriptive — discuss relationships between findings
- In the Research Gaps section, include both gaps and open questions

Use the following material:

**Papers:**
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

    try:
        response = client.chat.completions.create(
            model="gpt-5.4",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content.strip()
    except APIError as e:
        raise RuntimeError(f"OpenAI API error in synthesise_literature_review: {e}") from e
