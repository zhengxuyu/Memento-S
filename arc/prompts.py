"""Prompt construction for the ReactAgent."""
from __future__ import annotations

import textwrap
from typing import Any


def build_func_resp_prompt(
    latest_frame: Any,
    frames: list,
    last_action_name: str,
    retry_count: int,
    current_steps: list,
    max_retries: int | None = None,
    action_history: str = "",
) -> str:
    """Build the observation prompt — just raw game state, no programmatic help."""
    sections: list[str] = []

    # Game state
    score = getattr(latest_frame, "score", latest_frame.levels_completed)
    sections.append(f"# Game State: {latest_frame.state.name} | Score: {score}")

    # Retry info
    if retry_count > 0:
        attempt_str = f"Attempt {retry_count + 1}"
        if max_retries is not None:
            attempt_str += f"/{max_retries + 1}"
        sections.append(
            f"# {attempt_str} — review past failures and try a DIFFERENT strategy."
        )

    # Raw grid
    if latest_frame.frame:
        for i, grid in enumerate(latest_frame.frame):
            sections.append(f"# Grid {i}:")
            for row in grid:
                sections.append(f"  {row}")

    # Simple diff: did something change?
    if len(frames) > 1 and frames[-2].frame and latest_frame.frame:
        prev_grid = frames[-2].frame[0]
        curr_grid = latest_frame.frame[0]
        if prev_grid == curr_grid:
            sections.append(f"# Last action ({last_action_name}): NO EFFECT (wall hit or no-op)")
        else:
            sections.append(f"# Last action ({last_action_name}): grid changed")

    # Action history (last N actions)
    if action_history:
        sections.append(action_history)

    # Budget
    n_steps = len(current_steps)
    sections.append(f"# Step {n_steps + 1} | Actions used: {n_steps}")

    # Instruction
    sections.append("# ACT NOW — call exactly one ACTION1-ACTION6 or update_game_notes.")

    return "\n\n".join(sections)


def build_user_prompt() -> str:
    """Minimal user prompt — strategy comes from skills."""
    return textwrap.dedent("""\
        You are playing an ARC-AGI-3 grid game. Discover the rules yourself.
        ALWAYS call exactly one tool: ACTION1-ACTION6 or update_game_notes.
    """)
