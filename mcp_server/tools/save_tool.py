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


def _reviews_dir() -> Path:
    """Return storage/reviews/ at the project root (mcp_server/tools/ -> root)."""
    return Path(__file__).resolve().parent.parent.parent / "storage" / "reviews"


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
    reviews_dir = _reviews_dir()
    reviews_dir.mkdir(parents=True, exist_ok=True)

    # Build a filesystem-safe filename
    now = datetime.now(timezone.utc)
    timestamp_str = now.strftime("%Y%m%d_%H%M%S")
    topic_slug = slugify(topic, max_length=60, word_boundary=True) or "review"

    # Assemble the full record to persist
    record: dict[str, Any] = {
        "topic": topic,
        "saved_at": now.isoformat(),
        "review_markdown": review_markdown,
        "metadata": metadata,
    }

    payload = json.dumps(record, indent=2, ensure_ascii=False)

    # Exclusive create ('x') so two saves of the same topic within the same
    # second get distinct files instead of silently overwriting each other
    suffix = 1
    while True:
        filename = f"{timestamp_str}_{topic_slug}{'' if suffix == 1 else f'-{suffix}'}.json"
        filepath = reviews_dir / filename
        try:
            with filepath.open("x", encoding="utf-8") as f:
                f.write(payload)
            break
        except FileExistsError:
            suffix += 1

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
    reviews_dir = _reviews_dir()

    if not reviews_dir.exists():
        return []

    summaries: list[dict[str, Any]] = []
    for json_file in reviews_dir.glob("*.json"):
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

    # Newest first; ISO 8601 UTC timestamps sort correctly as strings
    summaries.sort(key=lambda r: (r["saved_at"], r["filename"]), reverse=True)
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
        ValueError: If the filename is invalid or the file contains invalid JSON.
    """
    reviews_dir = _reviews_dir().resolve()
    filepath = (reviews_dir / filename).resolve()

    # Only allow plain *.json names inside storage/reviews/ (no path traversal)
    if filepath.parent != reviews_dir or filepath.suffix != ".json":
        raise ValueError(f"Invalid review filename: {filename}")

    if not filepath.is_file():
        raise FileNotFoundError(f"Review file not found: {filename}")

    try:
        return json.loads(filepath.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"Review file contains invalid JSON: {e}") from e
