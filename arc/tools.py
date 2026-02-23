"""Tool definitions for the ReactBufferAgent."""
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from arcengine import GameAction

from arc.config import KNOWLEDGE_HEADERS

# ---------------------------------------------------------------------------
# Skill version tracking
# ---------------------------------------------------------------------------

_skill_version_counter: int = 0


def _save_skill_version(
    skill_path: Path,
    section: str,
    content: str,
    score: int | None = None,
    trigger: str = "agent_note",
) -> None:
    """Save a timestamped snapshot of SKILL.md after each change.

    Writes to ``skill_versions/`` next to the SKILL.md file:
      v001_20260217_143322_level_strategies_score1_agent_note.md
    Also appends a line to ``skill_versions/changelog.jsonl``.
    """
    global _skill_version_counter
    _skill_version_counter += 1

    versions_dir = skill_path.parent / "skill_versions"
    versions_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    score_tag = f"score{score}" if score is not None else "score_unknown"
    fname = f"v{_skill_version_counter:03d}_{ts}_{section}_{score_tag}_{trigger}.md"

    # Copy current SKILL.md as the snapshot
    dst = versions_dir / fname
    shutil.copy2(skill_path, dst)

    # Append to changelog
    changelog = versions_dir / "changelog.jsonl"
    entry = {
        "version": _skill_version_counter,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "section": section,
        "trigger": trigger,
        "score": score,
        "content_preview": content[:200],
        "snapshot": fname,
    }
    with open(changelog, "a", encoding="utf-8") as f:
        json.dump(entry, f, ensure_ascii=False)
        f.write("\n")


def build_react_tools(base_functions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extend base LLM game action tools with update_game_notes.

    Only ACTION1-ACTION6 (from base_functions) are valid game actions.
    navigate_to and execute_plan have been removed — the LLM must choose
    atomic actions directly.
    """
    functions = list(base_functions)
    functions.append({
        "name": "update_game_notes",
        "description": (
            "Record discovered game knowledge to your persistent skill file. "
            "Use this to save confirmed action mappings, game rules, level "
            "strategies, object roles, or tips. Knowledge persists across retries."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "section": {
                    "type": "string",
                    "enum": list(KNOWLEDGE_HEADERS.keys()),
                    "description": "Which knowledge section to update.",
                },
                "content": {
                    "type": "string",
                    "description": "The knowledge to record, in markdown format.",
                },
                "replace": {
                    "type": "string",
                    "enum": ["true", "false"],
                    "description": "Replace entire section (true) or append (false).",
                },
            },
            "required": ["section", "content", "replace"],
            "additionalProperties": False,
        },
    })
    return functions


def handle_game_notes_update(
    arguments_json: str,
    skill_path: Any,
    score: int | None = None,
    trigger: str = "agent_note",
) -> str:
    """Process an update_game_notes tool call -- write to SKILL.md.

    Args:
        arguments_json: JSON string with section, content, replace.
        skill_path: Path to the SKILL.md file.
        score: Current game score (for version tracking).
        trigger: What caused this update ('agent_note', 'level_summary', 'skill_evolution').

    Returns:
        Status message string.
    """
    try:
        args = json.loads(arguments_json)
    except json.JSONDecodeError:
        return "Error: invalid JSON arguments."

    section = args.get("section", "")
    content = args.get("content", "").strip()
    replace = args.get("replace", "false") == "true"

    if section not in KNOWLEDGE_HEADERS:
        return f"Error: unknown section '{section}'. Valid: {list(KNOWLEDGE_HEADERS.keys())}"
    if not content:
        return "Error: content is empty."

    skill_path = Path(skill_path)
    if not skill_path.exists():
        return f"Error: skill file not found at {skill_path}"

    try:
        text = skill_path.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading skill file: {e}"

    header = KNOWLEDGE_HEADERS[section]
    header_idx = text.find(header)
    if header_idx < 0:
        text = text.rstrip() + f"\n\n{header}\n{content}\n"
    else:
        newline_after = text.find("\n", header_idx)
        if newline_after < 0:
            newline_after = len(text)
        content_start = newline_after + 1

        next_header_idx = len(text)
        search_start = content_start
        for h in KNOWLEDGE_HEADERS.values():
            pos = text.find(h, search_start)
            if pos > 0 and pos < next_header_idx:
                next_header_idx = pos
        pos = text.find("\n## ", search_start)
        if pos >= 0 and pos + 1 < next_header_idx:
            next_header_idx = pos + 1

        old_content = text[content_start:next_header_idx].strip()

        if replace:
            new_content = content
        else:
            if old_content and old_content != "(no data yet)":
                new_content = old_content + "\n" + content
            else:
                new_content = content

        text = text[:content_start] + new_content + "\n\n" + text[next_header_idx:]

    try:
        skill_path.write_text(text, encoding="utf-8")
    except Exception as e:
        return f"Error writing skill file: {e}"

    # Save versioned snapshot
    try:
        _save_skill_version(skill_path, section, content, score=score, trigger=trigger)
    except Exception:
        pass  # Version tracking is best-effort

    return f"Updated '{section}'. Knowledge will inform your future decisions."
