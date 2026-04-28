"""
save_tool.py — Tool for persisting literature reviews to local JSON files.

Reviews are saved to storage/reviews/{timestamp}_{slug}.json relative to
the project root (two levels up from this file).
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from slugify import slugify


def save_review(
    topic: str, review_markdown: str, metadata: dict[str, Any]
) -> dict[str, str]:
    """
    Save a completed literature review as a JSON file.

    The file is named  {timestamp}_{slug}.json  where:
        timestamp  is UTC in the format YYYYMMDD_HHMMSS
        slug       is a URL-safe version of the topic string

    Args:
        topic: The research topic string (used to generate the filename).
        review_markdown: The Markdown review text to persist.
        metadata: Arbitrary metadata dict (e.g. paper count, source breakdown).

    Returns:
        A dict with keys:
            filepath  — absolute path to the saved file (as string)
            saved_at  — ISO 8601 UTC timestamp of when the file was written
    """
    # Resolve the storage/reviews directory relative to this file's location
    # mcp_server/tools/ -> mcp_server/ -> project root -> storage/reviews/
    project_root = Path(__file__).resolve().parent.parent.parent
    reviews_dir = project_root / "storage" / "reviews"
    reviews_dir.mkdir(parents=True, exist_ok=True)

    # Build a filesystem-safe filename
    now = datetime.now(timezone.utc)
    timestamp_str = now.strftime("%Y%m%d_%H%M%S")
    topic_slug = slugify(topic, max_length=60, word_boundary=True)
    filename = f"{timestamp_str}_{topic_slug}.json"
    filepath = reviews_dir / filename

    # Assemble the full record to persist
    record: dict[str, Any] = {
        "topic": topic,
        "saved_at": now.isoformat(),
        "review_markdown": review_markdown,
        "metadata": metadata,
    }

    filepath.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "filepath": str(filepath),
        "saved_at": now.isoformat(),
        "filename": filename,
    }


def list_reviews() -> list[dict[str, Any]]:
    """
    List all saved reviews in the storage/reviews directory.

    Returns:
        A list of summary dicts, each with keys:
            topic, saved_at, filepath, filename.
        Sorted by saved_at descending (newest first).
    """
    project_root = Path(__file__).resolve().parent.parent.parent
    reviews_dir = project_root / "storage" / "reviews"

    if not reviews_dir.exists():
        return []

    summaries: list[dict[str, Any]] = []
    for json_file in sorted(reviews_dir.glob("*.json"), reverse=True):
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
            summaries.append(
                {
                    "topic": data.get("topic", ""),
                    "saved_at": data.get("saved_at", ""),
                    "filepath": str(json_file),
                    "filename": json_file.name,
                }
            )
        except (json.JSONDecodeError, OSError):
            # Skip corrupted or unreadable files
            continue

    return summaries


def load_review(filename: str) -> dict[str, Any]:
    """
    Load a specific review by filename.

    Args:
        filename: The JSON filename (e.g. "20240128_143022_transformers.json").

    Returns:
        The full review record dict.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file contains invalid JSON.
    """
    project_root = Path(__file__).resolve().parent.parent.parent
    filepath = project_root / "storage" / "reviews" / filename

    if not filepath.exists():
        raise FileNotFoundError(f"Review file not found: {filename}")

    try:
        return json.loads(filepath.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"Review file contains invalid JSON: {e}") from e
