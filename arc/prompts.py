"""Prompt construction for the ReactBufferAgent."""
from __future__ import annotations

import textwrap
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from arcengine import FrameData


def build_func_resp_prompt(
    latest_frame: Any,
    frames: list,
    perception: Any,
    last_action_name: str,
    retry_count: int,
    interaction_tracker: Any,
    transformation_detector: Any,
    inventory: Any,
    navigator: Any,
    get_player_position: Any,
    build_buffer_context: Any,
    build_action_history: Any,
    build_loop_warning: Any,
    build_stuck_warning: Any,
    current_steps: list,
    max_retries: int | None = None,
    trigger_causal_alert: str = "",
    first_look_analysis: str = "",
    region_similarities: str = "",
    hypotheses_text: str = "",
    belief_summary: str = "",
    failure_analysis: str = "",
) -> str:
    """Observation prompt: perception data + buffer context + game intelligence."""
    sections: list[str] = []

    # Game state
    score = getattr(latest_frame, "score", latest_frame.levels_completed)
    sections.append(f"# Game State: {latest_frame.state.name} | Score: {score}")

    # Causal alert — most important info, show first
    if trigger_causal_alert:
        sections.append(trigger_causal_alert)

    # Retry info + failure analysis
    if retry_count > 0:
        attempt_str = f"Attempt {retry_count + 1}"
        if max_retries is not None:
            attempt_str += f"/{max_retries + 1}"
        sections.append(
            f"# {attempt_str} — "
            f"review past failures and try a DIFFERENT strategy."
        )
        if failure_analysis:
            sections.append(f"# LAST ATTEMPT ANALYSIS\n{failure_analysis}")

    # Belief summary (Layer 2: what the agent knows)
    if belief_summary:
        sections.append(f"# AGENT BELIEFS\n{belief_summary}")

    n_steps = len(current_steps)

    # First-look analysis (big-picture context for early steps)
    if first_look_analysis and n_steps < 10:
        sections.append(
            "# GLOBAL LAYOUT ANALYSIS (from first look)\n"
            + first_look_analysis
        )

    # Region similarities (algorithmic detection, early steps)
    if region_similarities and n_steps < 15:
        sections.append(region_similarities)

    # Hypotheses to test (early steps)
    if hypotheses_text and n_steps < 15:
        sections.append(hypotheses_text)

    # Structured perception
    prev_frame_grids = None
    if len(frames) > 1 and frames[-2].frame:
        prev_frame_grids = frames[-2].frame

    if latest_frame.frame:
        perception_text = perception.describe_frame(
            frame=latest_frame.frame,
            prev_frame=prev_frame_grids,
            last_action=last_action_name or None,
        )
        sections.append(perception_text)

        # Game intelligence
        grid = latest_frame.frame[0]
        analysis = perception.analyze_grid(grid)

        player_pos = get_player_position()
        navigator.update_action_mappings(perception._action_effects)
        if not navigator._initialized:
            navigator.infer_floor_and_walls(grid, analysis.bg_color)
        else:
            navigator.refresh_walkability(grid, analysis.bg_color)

        if player_pos:
            qr = (player_pos[0] // 5) * 5
            qc = (player_pos[1] // 5) * 5
            navigator.memory.record_walkable((qr, qc))
            navigator.memory.record_visit((qr, qc))

        # Update inventory
        player_colors = set()
        if perception._player_obj is not None:
            player_colors.add(perception._player_obj.color)
        for c, count in perception._player_color_votes.items():
            if count >= 1:
                player_colors.add(c)

        inventory.update_from_analysis(
            objects=analysis.objects,
            bg_color=analysis.bg_color,
            player_pos=player_pos,
            player_colors=player_colors,
            step=len(current_steps),
            interaction_rules=interaction_tracker.get_rules(),
        )
        inventory.update_distances(player_pos, navigator)

    # Game intelligence sections
    rules_summary = interaction_tracker.get_rules_summary()
    if rules_summary:
        sections.append(rules_summary)
    toggle_warnings = interaction_tracker.get_toggle_warnings()
    if toggle_warnings:
        sections.append(toggle_warnings)
    recent_events = interaction_tracker.get_recent_events(3)
    if recent_events:
        sections.append(recent_events)
    transform_summary = transformation_detector.get_summary()
    if transform_summary:
        sections.append(transform_summary)
    trigger_summary = interaction_tracker.get_trigger_hypotheses_summary()
    if trigger_summary:
        sections.append(trigger_summary)

    # Post-trigger impact (only if no causal alert already covers it)
    if not trigger_causal_alert:
        transform_impact = transformation_detector.get_latest_impact()
        if transform_impact:
            sections.append(
                "# POST-TRIGGER IMPACT (what changed in the grid)\n"
                + transform_impact + "\n"
                "ACTION: Navigate to the changed region and check for new paths or entrances."
            )

    inventory_summary = inventory.get_inventory_summary()
    if inventory_summary:
        sections.append(inventory_summary)

    # Navigator status
    from arc.game_intelligence import ObjectStatus
    active_items = [
        item for item in inventory._items
        if item.status not in (ObjectStatus.COLLECTED, ObjectStatus.VISITED)
    ]
    active_items.sort(key=lambda i: i.distance_actions)
    target_info = [
        (item.position[0], item.position[1], f"color {item.color} [{item.role}]")
        for item in active_items
    ]

    nav_player_pos = get_player_position()
    navigator_status = navigator.get_status_summary(
        player_pos=nav_player_pos,
        targets=target_info,
    )
    if navigator_status:
        sections.append(navigator_status)

    # Buffer context
    buffer_ctx = build_buffer_context()
    if buffer_ctx:
        sections.append(buffer_ctx)

    # Anti-repetition
    action_history = build_action_history()
    if action_history:
        sections.append(action_history)
    loop_warning = build_loop_warning()
    if loop_warning:
        sections.append(loop_warning)
    stuck_warning = build_stuck_warning()
    if stuck_warning:
        sections.append(stuck_warning)

    # Level transition hint
    levels_done = getattr(latest_frame, "levels_completed", 0)
    if levels_done > 0 and len(current_steps) < 5:
        sections.append(
            "# LEVEL TRANSITION\n"
            f"You just entered level {levels_done + 1}. "
            "The game mechanics from previous levels likely still apply.\n"
            "1. Check your game_notes for rules from previous levels\n"
            "2. Scan for SAME types of interactive objects\n"
            "3. Apply same prerequisite/collection strategy\n"
            "4. Use ACTION1-ACTION6 to navigate efficiently\n"
            "5. Use update_game_notes to record new discoveries"
        )

    # Object-focus reminder when stuck without scoring
    from arc.game_intelligence import ObjectStatus
    n_steps = len(current_steps)
    if n_steps > 15 and score == 0:
        active_objects = [
            item for item in inventory._items
            if item.status not in (ObjectStatus.COLLECTED, ObjectStatus.VISITED)
        ]
        special_objects = [
            item for item in active_objects
            if item.shape in ("cross", "diamond", "T-shape", "L-shape", "U-shape")
        ]
        if active_objects:
            obj_focus_parts = [
                f"# FOCUS ON OBJECTS ({len(active_objects)} remaining, "
                f"{len(special_objects)} special shapes)",
                "Your goal is to INTERACT with objects, not explore empty areas.",
                "Step DIRECTLY ON each object and observe what happens to the grid.",
            ]
            if special_objects:
                obj_focus_parts.append(
                    "PRIORITY targets (special shapes — likely triggers or keys):"
                )
                for item in special_objects[:3]:
                    obj_focus_parts.append(
                        f"  -> {item.shape.upper()} color {item.color} at "
                        f"({item.position[0]},{item.position[1]})"
                    )
            sections.append("\n".join(obj_focus_parts))

    # Instruction — keep short to save tokens
    sections.append(
        "# ACT NOW — call exactly one ACTION1-ACTION6."
    )

    return "\n\n".join(sections)


def build_user_prompt() -> str:
    """Minimal user prompt -- strategy is in the skills system prompt."""
    return textwrap.dedent("""\
        You are playing an ARC-AGI-3 grid game. Follow your skills.
        ALWAYS call exactly one tool: ACTION1, ACTION2, ACTION3, ACTION4, ACTION5, or ACTION6.
    """)
