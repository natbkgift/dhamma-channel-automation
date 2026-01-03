from __future__ import annotations

import json
from pathlib import Path


def write_post_templates(base_dir: Path) -> None:
    templates_dir = base_dir / "templates" / "post"
    templates_dir.mkdir(parents=True, exist_ok=True)
    (templates_dir / "short.md").write_text(
        "{{hook}}\n{{summary}}\n\n{{cta}}\n{{hashtags}}\n", encoding="utf-8"
    )
    (templates_dir / "long.md").write_text(
        "{{title}}\n\n{{hook}}\n\n{{summary}}\n\n{{cta}}\n\n{{hashtags}}\n",
        encoding="utf-8",
    )


def write_metadata(
    base_dir: Path,
    run_id: str,
    *,
    title: str = "Sample title",
    description: str = "Sample description",
    tags: list[str] | None = None,
    language: str = "en",
    platform: str = "youtube",
) -> Path:
    """
    Write metadata.json for testing purposes.
    
    Args:
        base_dir: Base directory (usually tmp_path in tests)
        run_id: Run identifier
        title: Video title
        description: Video description
        tags: List of tags (default: ["#test"])
        language: Language code (default: "en")
        platform: Platform name (default: "youtube")
    
    Returns:
        Path to the created metadata.json file
    """
    if tags is None:
        tags = ["#test"]
    
    metadata_path = base_dir / "output" / run_id / "metadata.json"
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "title": title,
        "description": description,
        "tags": tags,
        "language": language,
        "platform": platform,
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return metadata_path
