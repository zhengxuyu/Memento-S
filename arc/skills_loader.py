"""Load local skills for system prompt injection."""
from __future__ import annotations

import logging
import re
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


def _extract_frontmatter(content: str) -> tuple[str, str]:
    """Extract name and description from YAML frontmatter.

    Returns (name, description). Falls back to ("", "") if not found.
    """
    m = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not m:
        return "", ""
    fm = m.group(1)
    name = ""
    desc = ""
    in_desc = False
    for line in fm.splitlines():
        if line.startswith("name:"):
            name = line.split(":", 1)[1].strip().strip("\"'")
            in_desc = False
        elif line.startswith("description:"):
            val = line.split(":", 1)[1].strip().strip("\"'>|")
            in_desc = True
            if val:
                desc = val
        elif in_desc and (line.startswith("  ") or line.startswith("\t")):
            # continuation of multi-line description
            piece = line.strip()
            if piece:
                desc = (desc + " " + piece).strip() if desc else piece
        else:
            in_desc = False
    return name, desc


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


def load_skill_summaries() -> list[tuple[str, str, str]]:
    """Load skill name + description only (no full content).

    Returns list of (dir_name, skill_name, description).
    """
    for base in _get_skills_dirs():
        if not base.is_dir():
            continue
        result: list[tuple[str, str, str]] = []
        try:
            for sub in sorted(base.iterdir()):
                if not sub.is_dir():
                    continue
                for fname in SKILL_FILENAMES:
                    f = sub / fname
                    if f.is_file():
                        content = _read_skill_file(f)
                        if content:
                            name, desc = _extract_frontmatter(content)
                            name = name or sub.name
                            desc = desc or "(no description)"
                            result.append((sub.name, name, desc))
                        break
            if result:
                return result
        except Exception as e:
            logger.warning("Error scanning skills dir %s: %s", base, e)
    return []


def load_single_skill(name: str) -> tuple[str, str]:
    """Load one skill's full SKILL.md by dir name. Returns (matched_name, content).

    Tries: exact match → prefix → substring. Raises ValueError if not found.
    """
    all_dirs: list[tuple[str, Path]] = []
    for base in _get_skills_dirs():
        if not base.is_dir():
            continue
        try:
            for sub in sorted(base.iterdir()):
                if not sub.is_dir():
                    continue
                all_dirs.append((sub.name, sub))
        except Exception:
            continue

    if not all_dirs:
        raise ValueError("No skill directories found")

    query = name.lower().strip()

    # Exact match
    for dir_name, dir_path in all_dirs:
        if dir_name.lower() == query:
            content = _read_skill_content(dir_path)
            if content:
                return (dir_name, content)

    # Prefix match
    prefix_matches = [(n, p) for n, p in all_dirs if n.lower().startswith(query)]
    if len(prefix_matches) == 1:
        dir_name, dir_path = prefix_matches[0]
        content = _read_skill_content(dir_path)
        if content:
            return (dir_name, content)

    # Substring match
    substr_matches = [(n, p) for n, p in all_dirs if query in n.lower()]
    if len(substr_matches) == 1:
        dir_name, dir_path = substr_matches[0]
        content = _read_skill_content(dir_path)
        if content:
            return (dir_name, content)
    elif len(substr_matches) > 1:
        suggestions = [n for n, _ in substr_matches[:10]]
        raise ValueError(f"Ambiguous match for '{name}'. Did you mean: {', '.join(suggestions)}?")

    # Also check prefix_matches > 1
    if len(prefix_matches) > 1:
        suggestions = [n for n, _ in prefix_matches[:10]]
        raise ValueError(f"Ambiguous match for '{name}'. Did you mean: {', '.join(suggestions)}?")

    available = [n for n, _ in all_dirs[:20]]
    raise ValueError(f"No skill found matching '{name}'. Available: {', '.join(available)}")


def _read_skill_content(dir_path: Path) -> str:
    """Read SKILL.md content from a skill directory."""
    for fname in SKILL_FILENAMES:
        f = dir_path / fname
        if f.is_file():
            return _read_skill_file(f)
    return ""


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
