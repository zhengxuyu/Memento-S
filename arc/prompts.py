"""Prompt construction for the ReactAgent."""
from __future__ import annotations

import textwrap
from collections import Counter
from typing import Any


def _compact_grid(grid: list[list[int]]) -> str:
    """Compress a 2D grid into a sparse representation.

    Shows grid dimensions, background color, and only non-background cells.
    This reduces a 64x64 grid from ~30K chars to typically <2K chars.
    """
    if not grid or not grid[0]:
        return "(empty grid)"

    rows = len(grid)
    cols = len(grid[0])

    # Find background color (most common value)
    counter: Counter[int] = Counter()
    for row in grid:
        counter.update(row)
    bg = counter.most_common(1)[0][0]

    # Collect non-background cells, grouped by color
    color_cells: dict[int, list[tuple[int, int]]] = {}
    for r, row in enumerate(grid):
        for c, val in enumerate(row):
            if val != bg:
                color_cells.setdefault(val, []).append((r, c))

    lines = [f"{rows}x{cols} grid, background=color {bg}"]

    if not color_cells:
        lines.append("(all background)")
        return "\n".join(lines)

    for color in sorted(color_cells):
        cells = color_cells[color]
        if len(cells) > 50:
            # Summarize large regions with bounding box
            rs = [r for r, c in cells]
            cs = [c for r, c in cells]
            lines.append(
                f"color {color}: {len(cells)} cells, "
                f"rows {min(rs)}-{max(rs)}, cols {min(cs)}-{max(cs)}"
            )
        else:
            coords = ", ".join(f"({r},{c})" for r, c in cells)
            lines.append(f"color {color}: {coords}")

    return "\n".join(lines)


def _grid_diff(prev_grid: list[list[int]], curr_grid: list[list[int]]) -> str:
    """Show only cells that changed between two grids."""
    changes: list[str] = []
    for r, (prev_row, curr_row) in enumerate(zip(prev_grid, curr_grid)):
        for c, (pv, cv) in enumerate(zip(prev_row, curr_row)):
            if pv != cv:
                changes.append(f"  ({r},{c}): {pv}->{cv}")

    if not changes:
        return "No cells changed."
    if len(changes) > 80:
        return f"{len(changes)} cells changed (large-scale change).\nFirst 40:\n" + "\n".join(changes[:40])
    return f"{len(changes)} cells changed:\n" + "\n".join(changes)


def build_func_resp_prompt(
    latest_frame: Any,
    frames: list,
    last_action_name: str,
    retry_count: int,
    current_steps: list,
    max_retries: int | None = None,
    action_history: str = "",
    few_shot: str = "",
    thinking_tools: str = "",
) -> str:
    """Build the observation prompt — raw game state + few-shot + thinking tools."""
    sections: list[str] = []

    # Few-shot from episode memory (most important context, show first)
    if few_shot:
        sections.append(few_shot)

    # Situation-based thinking tools
    if thinking_tools:
        sections.append(thinking_tools)

    # Game state with level info
    score = getattr(latest_frame, "score", latest_frame.levels_completed)
    current_level = score + 1
    sections.append(
        f"# Game State: {latest_frame.state.name} | "
        f"Level: {current_level} (score={score} levels completed)"
    )

    # Level transition notice — when score just increased
    if current_steps:
        if len(current_steps) >= 2:
            prev_score = current_steps[-2].get("score", 0)
        else:
            prev_score = 0
        if score > prev_score and score > 0:
            sections.append(
                f"## LEVEL UP! You completed level {score} and are now on level {current_level}.\n"
                "The grid has reset to a new layout. The SAME core mechanics apply — "
                "use what you learned from previous levels. Update your skill file!"
            )

    # Retry info
    if retry_count > 0:
        attempt_str = f"Attempt {retry_count + 1}"
        if max_retries is not None:
            attempt_str += f"/{max_retries + 1}"
        sections.append(
            f"# {attempt_str} — review past failures and try a DIFFERENT strategy."
        )

    # Compact grid representation (sparse format)
    is_first_step = len(current_steps) == 0
    if latest_frame.frame:
        for i, grid in enumerate(latest_frame.frame):
            sections.append(f"# Grid {i} (compact):\n{_compact_grid(grid)}")

    # Grid diff: show what changed since last action
    if len(frames) > 1 and frames[-2].frame and latest_frame.frame:
        prev_grid = frames[-2].frame[0]
        curr_grid = latest_frame.frame[0]
        if prev_grid == curr_grid:
            sections.append(f"# Last action ({last_action_name}): NO EFFECT (wall hit or no-op)")
        else:
            diff = _grid_diff(prev_grid, curr_grid)
            sections.append(f"# Last action ({last_action_name}): {diff}")

    # Action history (last N actions)
    if action_history:
        sections.append(action_history)

    # Budget
    n_steps = len(current_steps)
    sections.append(f"# Step {n_steps + 1} | Actions used: {n_steps}")

    # Instruction
    sections.append("# ACT NOW — call a game action (ACTION1-ACTION6). Then call `update_skill` to record what you learned.")

    return "\n\n".join(sections)


def build_user_prompt() -> str:
    """Minimal user prompt — strategy comes from skills."""
    return textwrap.dedent("""\
        You are playing an ARC-AGI-3 grid game. Discover the rules yourself.
        ALWAYS call exactly one tool: ACTION1-ACTION6, load_skill, or update_skill.
    """)
