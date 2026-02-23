"""Load local skills for system prompt injection."""
from __future__ import annotations

import logging
from pathlib import Path

from arc.config import SKILLS_DIR

logger = logging.getLogger(__name__)

SKILL_FILENAMES = ("SKILL.md", "skill.md", "README.md")


def _get_skills_dirs() -> list[Path]:
    dirs: list[Path] = []
    p = Path(SKILLS_DIR)
    if not p.is_absolute():
        p = Path.cwd() / p
    dirs.append(p)
    dirs.append(Path.cwd() / "skills")
    return dirs


def _read_skill_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except Exception as e:
        logger.warning("Could not read skill %s: %s", path, e)
        return ""


def load_local_skills(max_content_chars: int = 0) -> list[tuple[str, str]]:
    """Load all local skills (full content)."""
    for base in _get_skills_dirs():
        if not base.is_dir():
            continue
        result: list[tuple[str, str]] = []
        try:
            for sub in sorted(base.iterdir()):
                if not sub.is_dir():
                    continue
                for fname in SKILL_FILENAMES:
                    f = sub / fname
                    if f.is_file():
                        content = _read_skill_file(f)
                        if content:
                            if max_content_chars > 0 and len(content) > max_content_chars:
                                content = content[:max_content_chars] + "\n\n... [truncated]"
                            result.append((sub.name, content))
                        break
            if result:
                logger.info("Loaded %d skill(s) from %s", len(result), base)
                return result
        except Exception as e:
            logger.warning("Error scanning skills dir %s: %s", base, e)
    return []


def format_skills_for_prompt(
    skills: list[tuple[str, str]],
    heading: str = "Available skills (follow when relevant):",
) -> str:
    if not skills:
        return ""
    parts = [heading, ""]
    for name, content in skills:
        parts.append(f"## {name}")
        parts.append(content)
        parts.append("")
    return "\n".join(parts).strip()
