"""Load local skills with semantic routing.

When the SkillRouter is available, it selects top-K relevant sections
based on game context (Memento-S semantic routing). Falls back to
full loading if routing is disabled or fails.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from arc.config import SKILLS_DIR

logger = logging.getLogger(__name__)

SKILL_FILENAMES = ("SKILL.md", "skill.md", "README.md")

# Singleton router instance (lazy-loaded)
_router: Optional["SkillRouter"] = None


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
    """Load all local skills (full content). Used as fallback."""
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


def get_router() -> "SkillRouter":
    """Get or create the singleton SkillRouter instance."""
    global _router
    if _router is None:
        from arc.skill_router import SkillRouter
        _router = SkillRouter()
        _router.build_index()
    return _router


def load_routed_skills(game_context: str, top_k: int = 8) -> str:
    """Load skill sections using semantic routing.

    Args:
        game_context: Text describing current game state (query for routing).
        top_k: Number of skill sections to select.

    Returns:
        Formatted skill sections string for system prompt injection.
    """
    try:
        router = get_router()
        content = router.route(game_context, top_k=top_k)
        if content:
            logger.info(
                "Routed %d sections for context: %s...",
                top_k, game_context[:60],
            )
            return content
    except Exception as e:
        logger.warning("Skill routing failed, falling back to full load: %s", e)

    # Fallback: full load
    return format_skills_for_prompt(load_local_skills(max_content_chars=8000))


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
