"""ReactBufferAgent: ReAct agent with episode buffer for ARC-AGI-3.

Dennett-inspired 4-layer cognitive architecture:
  Layer 0: Reflexes — wall recording, player tracking, score detection
  Layer 1: Competence w/o Comprehension — AutoPilot: action mapping, BFS nav
  Layer 2: Intentional Stance — BeliefState + systematic hypothesis testing
  Layer 3: Joycean Machine — LLM: structured thinking pumps, single merged call

Each step: try Layer 1 (autopilot) -> try Layer 2 (hypothesis) -> Layer 3 (LLM)
"""
from __future__ import annotations

import base64
import io
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Optional

import numpy as np
import openai
from arcengine import FrameData, GameAction, GameState
from openai import OpenAI as OpenAIClient

from arc.checkpoint import (
    load_checkpoint,
    save_checkpoint,
    save_level_replay,
)
from arc.config import (
    BUFFER_CAPACITY,
    CHECKPOINT_DIR,
    CHECKPOINT_INTERVAL,
    EMB_DIM,
    MAX_ACTIONS,
    MAX_RETRIES,
    MESSAGE_LIMIT,
    NUM_RETRIEVE,
    SKILLS_DIR,
)
from arc.episode_buffer import EpisodeBuffer, GameEpisode, StepRecord
from arc.episode_embedding import EpisodeEmbedding
from arc.game_intelligence import (
    GameHypothesis,
    GridNavigator,
    HypothesisEngine,
    InteractionTracker,
    ObjectInventory,
    RegionComparator,
    TransformationDetector,
)
from arc.grid_perception import GridPerception
from arc.llm_agent import LLM
from arc.loop_detector import LoopDetector
from arc.prompts import (
    build_func_resp_prompt,
    build_user_prompt,
)
from arc.autopilot import AutoPilot
from arc.skill_evolution import SkillEvolution
from arc.skill_router import SkillRouter
from arc.tools import build_react_tools, handle_game_notes_update

logger = logging.getLogger(__name__)


class ReactBufferAgent(LLM):
    """ReAct agent with episode buffer, perception, and game intelligence."""

    MESSAGE_LIMIT: int = MESSAGE_LIMIT
    DO_OBSERVATION: bool = True

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        # Perception
        self.perception = GridPerception()

        # Episode buffer
        self.episode_buffer = EpisodeBuffer(
            capacity=BUFFER_CAPACITY, emb_dim=EMB_DIM,
        )
        self.embedder = EpisodeEmbedding(dim=EMB_DIM)

        # Game intelligence
        self.navigator = GridNavigator()
        self.interaction_tracker = InteractionTracker()
        self.inventory = ObjectInventory()
        self.transformation_detector = TransformationDetector()

        # Region comparison + hypothesis engine
        self.region_comparator = RegionComparator()
        self.hypothesis_engine = HypothesisEngine()

        # First-look analysis state (reset per episode)
        self._first_look_analysis: str = ""
        self._region_similarities: str = ""
        self._hypotheses: list[GameHypothesis] = []
        self._hypotheses_text: str = ""

        # Loop detection
        self.loop_detector = LoopDetector()

        # Episode state
        self.current_steps: list[StepRecord] = []
        self.current_step_embeddings: list[np.ndarray] = []
        self.retry_count: int = 0
        self.total_reasoning_tokens: int = 0
        self.last_action_name: str = ""
        self._last_score: int = 0

        # Navigate target failure tracking — blacklist after repeated failures
        self._navigate_failures: dict[tuple[int, int], int] = {}
        self._NAVIGATE_BLACKLIST_THRESHOLD = 1  # reject after N failures (was 3)

        # Region visit tracking — block areas visited too often without scoring
        self._region_visits: dict[tuple[int, int], int] = {}  # quantized (qr, qc) -> count
        self._region_last_score: dict[tuple[int, int], int] = {}  # last score when visited
        self._REGION_VISIT_LIMIT = 4  # block after N visits without score increase

        # Trigger causal alert — set when a trigger is detected, consumed in next observation
        self._trigger_causal_alert: str = ""

        # Reachability info from first-look flood-fill
        self._reachability_info: str = ""

        # Skill evolution (Memento-S: self-evolving skills)
        self.skill_path = Path(SKILLS_DIR) / "arc_game_playing" / "SKILL.md"
        self.evolution = SkillEvolution(self.game_id, self.skill_path)

        # Skill router (Memento-S: semantic skill routing)
        self._skill_router = SkillRouter()
        self._game_context: str = ""  # Updated each turn for routing

        # AutoPilot (Layers 1+2: algorithmic decision-making)
        self.autopilot = AutoPilot(
            navigator=self.navigator,
            inventory=self.inventory,
            interaction_tracker=self.interaction_tracker,
            perception=self.perception,
        )

    # ------------------------------------------------------------------
    # Tool definitions — ACTION1-6 + update_game_notes only
    # ------------------------------------------------------------------

    def build_functions(self) -> list[dict[str, Any]]:
        base = super().build_functions()
        # Filter to only ACTION1-ACTION6 (remove RESET — the agent handles resets internally)
        valid = {"ACTION1", "ACTION2", "ACTION3", "ACTION4", "ACTION5", "ACTION6"}
        base = [f for f in base if f["name"] in valid]
        return build_react_tools(base)

    # ------------------------------------------------------------------
    # Main loop — override Agent.main() for retry/episode management
    # ------------------------------------------------------------------

    def main(self) -> None:
        self.timer = time.time()
        self._try_load_checkpoint()

        while True:
            result = self._play_episode()

            if result == "win":
                self.evolution.record_outcome(True)
                logger.info(
                    "WIN on attempt %d! Total actions: %d, time: %.1fs",
                    self.retry_count + 1, self.action_counter, self.seconds,
                )
                break
            elif result in ("game_over", "max_actions"):
                self.evolution.record_outcome(False)

                # Skill evolution DISABLED — adds ~1000 tokens/turn of
                # unvalidated noise to prompts without improving play.
                # loop_analysis = self.loop_detector.analyze(self.current_steps)
                # self.evolution.analyze_and_evolve(...)
                # self._skill_router = SkillRouter()

                self.retry_count += 1
                if self.retry_count >= MAX_RETRIES:
                    logger.info("Max retries (%d) exhausted, stopping", MAX_RETRIES)
                    break
                logger.info(
                    "%s — retrying (attempt #%d), score=%d, actions=%d",
                    result.upper(), self.retry_count + 1,
                    self._last_score, self.action_counter,
                )
                self._reset_for_retry()
            else:
                logger.info("Episode ended: %s", result)
                break

        self.cleanup()

    # ------------------------------------------------------------------
    # Play one episode (RESET to WIN/GAME_OVER)
    # ------------------------------------------------------------------

    def _play_episode(self) -> str:
        """Play one episode. Returns 'win', 'game_over', or 'max_actions'.

        Layered dispatch each step:
          Layer 1 (AutoPilot) -> Layer 2 (Hypothesis) -> Layer 3 (LLM)
        """
        # Reset game
        frame = self.take_action(GameAction.RESET)
        if frame:
            self.append_frame(frame)
        self.last_action_name = "RESET"
        self._last_score = self._frame_score(self.frames[-1])

        # First-look analysis: big-picture understanding before any actions
        self._perform_first_look()

        # Init conversation (for when LLM is needed)
        self.messages = []
        self.push_message({"role": "user", "content": build_user_prompt()})
        self._latest_tool_call_id = "init_reset"
        self.push_message({
            "role": "assistant",
            "tool_calls": [{
                "id": self._latest_tool_call_id,
                "type": "function",
                "function": {"name": "RESET", "arguments": "{}"},
            }],
        })

        step_count = 0
        while True:
            latest = self.frames[-1]

            # Check terminal states
            if latest.state is GameState.WIN:
                self._finalize_episode(True)
                return "win"
            if latest.state is GameState.GAME_OVER:
                self._finalize_episode(False)
                return "game_over"
            if self.action_counter >= MAX_ACTIONS:
                logger.info("Max actions (%d) reached, ending episode", MAX_ACTIONS)
                self._finalize_episode(False)
                return "max_actions"

            player_pos = self._get_player_position()
            prev_score = self._last_score
            prev_grid = latest.frame[0] if latest.frame else None

            # ── Layer 1: AutoPilot (zero LLM calls) ──
            if self.autopilot.should_autopilot(step_count, self._last_score):
                action = self.autopilot.choose_action(player_pos, prev_grid)
                if action:
                    prev_pos = player_pos
                    self._execute_single_action(action, "{}")
                    curr_pos = self._get_player_position()
                    curr_grid = self.frames[-1].frame[0] if self.frames[-1].frame else None
                    grid_changed = prev_grid != curr_grid if prev_grid and curr_grid else False
                    self.autopilot.update_after_action(
                        action=action,
                        prev_pos=prev_pos,
                        curr_pos=curr_pos,
                        score_delta=self._last_score - prev_score,
                        grid_changed=grid_changed,
                    )
                    self._latest_tool_call_id = f"autopilot_{self.action_counter}"
                    step_count += 1
                    # Checkpoint + video
                    if self.action_counter % CHECKPOINT_INTERVAL == 0:
                        self._save_checkpoint()
                    if self.action_counter % 5 == 0:
                        self._generate_live_video()
                    continue

            # ── Layer 2: Hypothesis Testing ──
            hyp_action = self._run_hypothesis_test()
            if hyp_action:
                prev_pos = player_pos
                prev_grid_snap = prev_grid
                self._execute_single_action(hyp_action, "{}")
                curr_pos = self._get_player_position()
                curr_grid = self.frames[-1].frame[0] if self.frames[-1].frame else None
                grid_changed = prev_grid_snap != curr_grid if prev_grid_snap and curr_grid else False
                self._evaluate_hypothesis(
                    prev_grid_snap, curr_grid,
                    self._last_score - prev_score,
                    prev_pos, curr_pos,
                )
                self.autopilot.update_after_action(
                    action=hyp_action,
                    prev_pos=prev_pos,
                    curr_pos=curr_pos,
                    score_delta=self._last_score - prev_score,
                    grid_changed=grid_changed,
                )
                self._latest_tool_call_id = f"hypothesis_{self.action_counter}"
                step_count += 1
                if self.action_counter % CHECKPOINT_INTERVAL == 0:
                    self._save_checkpoint()
                if self.action_counter % 5 == 0:
                    self._generate_live_video()
                continue

            # ── Layer 3: LLM (single merged call — thinking pump + action) ──
            obs = self._build_observation(latest)
            self._update_game_context()

            action_call, reasoning = self._llm_think_and_act(obs, latest)
            if action_call:
                tc_name, tc_args, tc_id = action_call
                self._latest_tool_call_id = tc_id
                steps_before = len(self.current_steps)
                self._execute_single_action(tc_name, tc_args)
                # Attach reasoning to step
                if reasoning and len(self.current_steps) > steps_before:
                    self.current_steps[steps_before].reasoning = reasoning
            else:
                logger.warning("LLM failed to produce action, skipping turn")
                # Push a dummy tool_call_id so conversation stays valid
                self._latest_tool_call_id = f"skip_{self.action_counter}"

            step_count += 1
            if self.action_counter % CHECKPOINT_INTERVAL == 0:
                self._save_checkpoint()
            if self.action_counter % 5 == 0:
                self._generate_live_video()

        self._finalize_episode(False)
        return "max_actions"

    # ------------------------------------------------------------------
    # First-look analysis (big-picture understanding after RESET)
    # ------------------------------------------------------------------

    def _perform_first_look(self) -> None:
        """Analyze the full grid layout before any actions.

        1. Run RegionComparator (algorithmic, cheap) to find similar regions
        2. Find special objects (crosses, diamonds, etc.)
        3. Call LLM once for big-picture layout analysis
        4. Generate hypotheses from all gathered intelligence
        """
        if not self.frames:
            return
        latest = self.frames[-1]
        if not latest.frame:
            return

        grid = latest.frame[0]
        try:
            analysis = self.perception.analyze_grid(grid)
        except Exception as e:
            logger.warning("First look: grid analysis failed: %s", e)
            return

        bg_color = analysis.bg_color

        # --- Step 1: Algorithmic region comparison ---
        try:
            self._region_similarities = self.region_comparator.get_similarity_summary(
                grid, bg_color,
            )
            if self._region_similarities:
                logger.info("First look region similarities:\n%s", self._region_similarities)
        except Exception as e:
            logger.warning("First look: region comparison failed: %s", e)
            self._region_similarities = ""

        # --- Step 2: Find special objects in the grid ---
        special_objects: list[tuple[int, int, str, int]] = []
        special_shapes = {"cross", "diamond", "T-shape", "L-shape", "U-shape"}
        for obj in analysis.objects:
            if obj.shape in special_shapes:
                special_objects.append((
                    int(obj.center_r), int(obj.center_c),
                    obj.shape, obj.color,
                ))
        # Also check composites
        try:
            from arc.grid_perception import _cluster_nearby_objects
            composites = _cluster_nearby_objects(analysis.objects)
            for comp in composites:
                shape = comp.get("shape", "")
                if shape in special_shapes:
                    cr, cc = comp.get("center", (0, 0))
                    color = comp.get("color", 0)
                    special_objects.append((int(cr), int(cc), shape, color))
        except Exception:
            pass

        # --- Step 2.5: Static wall detection + reachability analysis ---
        try:
            self.navigator.infer_floor_and_walls(grid, bg_color)

            # Protect special objects from being misclassified as walls.
            # Interactive objects (crosses, triggers, etc.) are non-bg colored
            # but MUST remain walkable targets.
            from arc.game_intelligence import STEP_SIZE as _STEP
            for obj in special_objects:
                r, c, shape, color = obj
                qr = (r // _STEP) * _STEP
                qc = (c // _STEP) * _STEP
                self.navigator.memory.record_walkable((qr, qc))

            player_pos = self._get_player_position()
            if player_pos is None:
                # Try to identify player from grid analysis
                if analysis.objects:
                    # Player is typically one of the smaller distinct objects
                    player_obj = self.perception._player_obj
                    if player_obj:
                        player_pos = (int(player_obj.center_r), int(player_obj.center_c))

            if player_pos:
                reachable = self.navigator.flood_fill_reachable(
                    player_pos[0], player_pos[1],
                )

                # Identify likely-unreachable targets (hypothesis, not hard blacklist).
                # The agent can still try — if navigation actually fails,
                # threshold=1 will blacklist after one real attempt.
                from arc.game_intelligence import STEP_SIZE
                unreachable_targets: list[tuple[int, int, str]] = []
                reachable_targets: list[tuple[int, int, str]] = []
                for obj in special_objects:
                    r, c, shape, color = obj
                    qr = (r // STEP_SIZE) * STEP_SIZE
                    qc = (c // STEP_SIZE) * STEP_SIZE
                    if (qr, qc) not in reachable:
                        unreachable_targets.append((r, c, shape))
                        logger.info(
                            "Likely unreachable (hypothesis): %s at (%d,%d)",
                            shape, r, c,
                        )
                    else:
                        reachable_targets.append((r, c, shape))

                # Build prompt hint — guide LLM to prioritize reachable targets
                self._reachability_info = ""
                parts: list[str] = []
                if reachable_targets:
                    lines = [f"  - {shape} at ({r},{c})" for r, c, shape in reachable_targets]
                    parts.append("REACHABLE targets (prioritize these):\n" + "\n".join(lines))
                if unreachable_targets:
                    lines = [f"  - {shape} at ({r},{c})" for r, c, shape in unreachable_targets]
                    parts.append(
                        "LIKELY UNREACHABLE (wall-blocked, try others first; "
                        "may need a passage or teleport):\n" + "\n".join(lines)
                    )
                if parts:
                    self._reachability_info = "\n".join(parts)
                    logger.info(
                        "Reachability: %d reachable, %d likely unreachable",
                        len(reachable_targets), len(unreachable_targets),
                    )
            else:
                self._reachability_info = ""
        except Exception as e:
            logger.warning("First look: wall detection/reachability failed: %s", e)
            self._reachability_info = ""

        # --- Step 3: LLM first-look analysis ---
        try:
            grid_image_b64 = self._render_frame_base64(latest)
            prompt_parts = [
                "You are analyzing a grid-based game layout BEFORE taking any actions.",
                "Describe the overall layout concisely. Identify:",
                "(a) Distinct rooms or areas (bounded regions, corridors, open spaces)",
                "(b) Door-like bordered structures or entrances",
                "(c) Special objects (crosses, triggers, switches) and their positions",
                "(d) Similar patterns in different areas that might need to be aligned",
                "(e) Likely game objective and recommended strategy",
                "",
                "Be SPECIFIC with coordinates. Keep under 200 words.",
            ]
            if self._region_similarities:
                prompt_parts.append(
                    f"\nAlgorithmic analysis found these region similarities:\n"
                    f"{self._region_similarities}"
                )
            if special_objects:
                obj_lines = [
                    f"  - {shape.upper()} (color {color}) at ({r},{c})"
                    for r, c, shape, color in special_objects
                ]
                prompt_parts.append(
                    "\nSpecial objects detected:\n" + "\n".join(obj_lines)
                )
            if self._reachability_info:
                prompt_parts.append(
                    f"\n{self._reachability_info}"
                )

            prompt = "\n".join(prompt_parts)

            messages: list[dict] = []
            if grid_image_b64:
                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{grid_image_b64}",
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                })
            else:
                messages.append({"role": "user", "content": prompt})

            client = self._get_client()
            create_kwargs: dict[str, Any] = {
                "model": self._model,
                "messages": messages,
            }
            if self._extra_body:
                create_kwargs["extra_body"] = self._extra_body
            response = client.chat.completions.create(**create_kwargs)
            self._first_look_analysis = response.choices[0].message.content or ""
            self.track_tokens(response.usage.total_tokens, self._first_look_analysis)
            logger.info("First look analysis:\n%s", self._first_look_analysis[:500])
        except Exception as e:
            logger.warning("First look: LLM analysis failed: %s", e)
            self._first_look_analysis = ""

        # --- Step 4: Generate hypotheses ---
        try:
            confirmed_triggers = list(self.interaction_tracker._trigger_patterns.values())
            self._hypotheses = self.hypothesis_engine.generate_hypotheses(
                region_similarities=self.region_comparator.find_similar_pairs(grid, bg_color),
                special_objects=special_objects,
                confirmed_triggers=confirmed_triggers,
                first_look_text=self._first_look_analysis,
            )
            self._hypotheses_text = HypothesisEngine.format_hypotheses(
                self._hypotheses,
            )
            if self._hypotheses_text:
                logger.info("Hypotheses generated:\n%s", self._hypotheses_text)

            # Import hypotheses into AutoPilot for systematic testing
            self.autopilot.import_hypotheses(self._hypotheses)
            if self.autopilot.beliefs.hypotheses:
                self.autopilot.beliefs.phase = "hypothesis_testing"
        except Exception as e:
            logger.warning("First look: hypothesis generation failed: %s", e)
            self._hypotheses = []
            self._hypotheses_text = ""

    # ------------------------------------------------------------------
    # Tool call processing
    # ------------------------------------------------------------------

    def _process_tool_calls(
        self, tool_calls: list[tuple[str, str, str]],
    ) -> Optional[tuple[str, str, str]]:
        """Process tool calls: handle update_game_notes, return first game action.

        Returns the first game action call, or None if only notes were called.
        """
        game_action_call: Optional[tuple[str, str, str]] = None

        for tc_name, tc_args, tc_id in tool_calls:
            if tc_name == "update_game_notes":
                result = handle_game_notes_update(
                    tc_args, self.skill_path,
                    score=self._last_score, trigger="agent_note",
                )
                self.push_message({
                    "role": "tool",
                    "tool_call_id": tc_id,
                    "content": result,
                })
                logger.info("Notes updated: %s", result[:100])
            elif game_action_call is None:
                # Only accept atomic game actions (ACTION1-6).
                # navigate_to/execute_plan/RESET are rejected so every
                # step is a deliberate single action chosen by the model.
                valid_names = {"ACTION1", "ACTION2", "ACTION3", "ACTION4",
                               "ACTION5", "ACTION6"}
                if tc_name not in valid_names:
                    logger.warning("Rejected non-atomic action '%s', asking model to re-choose", tc_name)
                    self.push_message({
                        "role": "tool",
                        "tool_call_id": tc_id,
                        "content": (
                            f"Error: '{tc_name}' is not allowed. "
                            f"You MUST choose exactly one of ACTION1-ACTION6. "
                            f"Think about which direction to move or which interaction to perform, "
                            f"then call ACTION1, ACTION2, ACTION3, ACTION4, ACTION5, or ACTION6."
                        ),
                    })
                    continue
                game_action_call = (tc_name, tc_args, tc_id)
            else:
                # Extra action — reject
                self.push_message({
                    "role": "tool",
                    "tool_call_id": tc_id,
                    "content": "Error: only one game action at a time.",
                })

        return game_action_call

    # ------------------------------------------------------------------
    # Action execution
    # ------------------------------------------------------------------

    def _execute_single_action(self, name: str, args_json: str) -> None:
        """Execute one game action and record the step."""
        try:
            data = json.loads(args_json) if args_json else {}
        except json.JSONDecodeError:
            data = {}

        action = GameAction.from_name(name)
        action.set_data(data)

        # Pre-action state
        prev_frame = self.frames[-1]
        prev_score = self._frame_score(prev_frame)
        prev_grid = prev_frame.frame[0] if prev_frame.frame else None
        prev_player_pos = self._get_player_position()

        # Execute
        frame = self.take_action(action)
        if frame:
            self.append_frame(frame)
        self.action_counter += 1
        self.last_action_name = name

        # Post-action state
        latest = self.frames[-1]
        curr_score = self._frame_score(latest)
        curr_grid = latest.frame[0] if latest.frame else None

        # Determine if grid changed
        moved = False
        diff_text = "no_change"
        if prev_grid and curr_grid:
            if prev_grid != curr_grid:
                diff_text = "grid_changed"
                moved = True

        # Quick player tracking update: detect movement from grid diff
        # This keeps _player_obj fresh during batch operations (navigate_to, execute_plan)
        # NOTE: Only update player tracking, NOT action effects — teleportation can
        # corrupt direction mappings if we learn effects from large displacements.
        if moved and prev_grid and curr_grid:
            try:
                change = self.perception.compute_diff(prev_grid, curr_grid)
                if change and change.moved:
                    analysis = self.perception.analyze_grid(curr_grid)
                    self.perception._update_player_tracking(change.moved, analysis)
            except Exception:
                pass  # Non-critical, just tracking

        curr_player_pos = self._get_player_position()

        # Record step
        step = StepRecord(
            state_text=latest.state.name,
            action=name,
            frame_diff=diff_text,
            score_before=prev_score,
            score_after=curr_score,
        )
        self.current_steps.append(step)

        # Step embedding
        ctx = f"{name} {diff_text} score:{curr_score}"
        emb = self.embedder.encode(ctx)
        self.current_step_embeddings.append(emb)

        # Update game intelligence
        player_pos = self._get_player_position()
        self.interaction_tracker.track_step(
            step_num=len(self.current_steps),
            prev_grid=prev_grid,
            curr_grid=curr_grid,
            player_pos=player_pos,
            score_before=prev_score,
            score_after=curr_score,
            action=name,
        )
        transform_events = self.transformation_detector.analyze_step(
            step_num=len(self.current_steps),
            prev_grid=prev_grid,
            curr_grid=curr_grid,
            player_pos=player_pos,
            action=name,
        )

        # Trigger correlation: if transformations occurred, check if player
        # was near a special-shaped object that could be the cause
        triggered: list[tuple[int, int, int]] = []
        if transform_events and prev_grid and player_pos:
            nearby_special = self._find_nearby_special_objects(
                prev_grid, player_pos,
            )
            if nearby_special:
                triggered = self.interaction_tracker.check_trigger_correlation(
                    step_num=len(self.current_steps),
                    player_pos=player_pos,
                    transformation_events=transform_events,
                    nearby_objects=nearby_special,
                )
                # Mark triggered objects as VISITED in inventory so
                # we stop re-navigating to them
                from arc.game_intelligence import ObjectStatus
                for trig_color, trig_r, trig_c in triggered:
                    for item in self.inventory._items:
                        if (
                            item.color == trig_color
                            and item.status not in (ObjectStatus.COLLECTED, ObjectStatus.VISITED)
                            and abs(item.position[0] - trig_r) <= 10
                            and abs(item.position[1] - trig_c) <= 10
                        ):
                            item.status = ObjectStatus.VISITED
                            item.role = "trigger"
                            logger.info(
                                "Marked trigger object color %d at (%d,%d) as VISITED "
                                "(role=trigger) — will not re-navigate",
                                trig_color, item.position[0], item.position[1],
                            )

        # Post-trigger impact analysis: what did the transform actually change?
        impact_text = ""
        if transform_events and prev_grid and curr_grid:
            bg_color = 0
            try:
                analysis = self.perception.analyze_grid(curr_grid)
                bg_color = analysis.bg_color
            except Exception:
                pass
            impact_text = self.transformation_detector.analyze_transform_impact(
                prev_grid, curr_grid, transform_events, bg_color,
            )

        # Build causal alert: "You stepped on X → Y changed"
        if triggered and impact_text:
            # Pick the first trigger for the alert
            trig_color, trig_r, trig_c = triggered[0]
            shape = "object"
            for r, c, s, col in self._find_nearby_special_objects(prev_grid, player_pos) if prev_grid and player_pos else []:
                if col == trig_color:
                    shape = s
                    break
            self._trigger_causal_alert = (
                f"⚡ CAUSE & EFFECT: You stepped on {shape.upper()} "
                f"(color {trig_color}) at ({trig_r},{trig_c}) → "
                f"{impact_text}\n"
                f"This object is a TRIGGER. Now go explore the affected area!"
            )

        # Update navigator: record wall (no move) or walkable (moved)
        # Detect teleportation: if displacement > STEP_SIZE, treat as wall
        from arc.game_intelligence import STEP_SIZE as _STEP
        is_teleport = False
        if prev_player_pos and curr_player_pos and prev_player_pos != curr_player_pos:
            tdr = abs(curr_player_pos[0] - prev_player_pos[0])
            tdc = abs(curr_player_pos[1] - prev_player_pos[1])
            if tdr > _STEP or tdc > _STEP:
                is_teleport = True
        if prev_player_pos:
            if is_teleport:
                # Record teleport-triggering position+direction as wall
                self.navigator.update_from_action_result(
                    player_pos=prev_player_pos,
                    action=name,
                    moved=False,
                    new_player_pos=None,
                )
            else:
                self.navigator.update_from_action_result(
                    player_pos=prev_player_pos,
                    action=name,
                    moved=moved,
                    new_player_pos=curr_player_pos if moved else None,
                )

        self._last_score = curr_score

        logger.info(
            "%s: %s -> %s (score %d->%d, action #%d)",
            self.game_id, name, diff_text,
            prev_score, curr_score, self.action_counter,
        )

        # On score increase, reset counters (allow re-exploration)
        if curr_score > prev_score:
            self._region_visits.clear()
            self._region_last_score.clear()
            self._navigate_failures.clear()
            self.interaction_tracker.update_trigger_score(curr_score)
            self._summarize_level_completion(prev_score, curr_score)

    def _handle_execute_plan(self, args_json: str) -> None:
        """Execute a multi-action plan, stopping on score change or no-effect."""
        try:
            data = json.loads(args_json)
        except json.JSONDecodeError:
            return

        actions_str = data.get("actions", "")
        action_names = [a.strip() for a in actions_str.split(",") if a.strip()]
        if not action_names:
            return

        # Cap plan length
        action_names = action_names[:3]
        plan_start_score = self._last_score

        for i, name in enumerate(action_names):
            # Check stop conditions
            latest = self.frames[-1]
            if latest.state in (GameState.WIN, GameState.GAME_OVER):
                break

            self._execute_single_action(name, "{}")

            # Stop on score change
            if self._last_score != plan_start_score:
                logger.info("execute_plan: score changed at step %d, stopping", i + 1)
                break

            # Stop on no effect (wall hit)
            if self.current_steps and "no_change" in self.current_steps[-1].frame_diff:
                logger.info("execute_plan: no effect at step %d, stopping", i + 1)
                break

    def _handle_navigate_to(self, args_json: str) -> None:
        """Use BFS navigator to compute path and execute action sequence."""
        from arc.game_intelligence import STEP_SIZE, _DIR_DELTAS
        try:
            data = json.loads(args_json) if args_json else {}
        except json.JSONDecodeError:
            data = {}

        target_r = int(data.get("row", 0))
        target_c = int(data.get("col", 0))
        player_pos = self._get_player_position()

        if player_pos is None:
            # Try to identify player from grid analysis before falling back
            if self.frames and self.frames[-1].frame:
                try:
                    grid = self.frames[-1].frame[0]
                    analysis = self.perception.analyze_grid(grid)
                    if self.perception._player_obj is not None:
                        player_pos = (
                            int(self.perception._player_obj.center_r),
                            int(self.perception._player_obj.center_c),
                        )
                        logger.info(
                            "navigate_to: recovered player position from grid analysis: %s",
                            player_pos,
                        )
                except Exception as e:
                    logger.warning("navigate_to: grid analysis for player failed: %s", e)
            if player_pos is None:
                logger.warning("navigate_to: no player position, returning to LLM")
                return

        # --- Region visit limit: block areas visited too often without scoring ---
        target_key = (
            (target_r // STEP_SIZE) * STEP_SIZE,
            (target_c // STEP_SIZE) * STEP_SIZE,
        )
        region_count = self._region_visits.get(target_key, 0)
        region_last_score = self._region_last_score.get(target_key, 0)
        curr_score = self._last_score
        if region_count >= self._REGION_VISIT_LIMIT and curr_score <= region_last_score:
            logger.warning(
                "navigate_to(%d,%d): REGION EXHAUSTED — visited %d times without "
                "scoring. Explore somewhere else!",
                target_r, target_c, region_count,
            )
            # Redirect to frontier instead of refusing entirely
            self.navigator.update_action_mappings(
                self.perception._action_effects
            )
            player_pos_now = self._get_player_position() or player_pos
            frontier = self.navigator.get_exploration_suggestions(player_pos_now, n=5)
            for fr, fc in frontier:
                fk = ((fr // STEP_SIZE) * STEP_SIZE, (fc // STEP_SIZE) * STEP_SIZE)
                if self._region_visits.get(fk, 0) < self._REGION_VISIT_LIMIT:
                    alt_path = self.navigator.navigate_to(
                        fr, fc, player_pos_now[0], player_pos_now[1], max_steps=15,
                    )
                    if alt_path:
                        logger.info(
                            "navigate_to: EXHAUSTION REDIRECT to (%d,%d) path=%s",
                            fr, fc, alt_path,
                        )
                        self._execute_navigate_path(
                            alt_path, fr, fc, player_pos_now,
                            STEP_SIZE, _DIR_DELTAS,
                        )
                        return
            # All frontiers also exhausted — try a single unblocked move
            qr = (player_pos[0] // STEP_SIZE) * STEP_SIZE
            qc = (player_pos[1] // STEP_SIZE) * STEP_SIZE
            for d in ["RIGHT", "LEFT", "DOWN", "UP"]:
                if not self.navigator.memory.is_blocked((qr, qc), d):
                    fallback = self.navigator._dir_to_action.get(d)
                    if fallback:
                        self._execute_single_action(fallback, "{}")
                        return
            return

        # Track this visit
        self._region_visits[target_key] = region_count + 1
        self._region_last_score[target_key] = curr_score

        # --- Target blacklist: reject repeatedly-failing targets ---
        fail_count = self._navigate_failures.get(target_key, 0)
        if fail_count >= self._NAVIGATE_BLACKLIST_THRESHOLD:
            logger.warning(
                "navigate_to(%d,%d): BLACKLISTED (failed %d times). "
                "Redirecting to exploration frontier.",
                target_r, target_c, fail_count,
            )
            # Force explore instead
            self.navigator.update_action_mappings(
                self.perception._action_effects
            )
            frontier = self.navigator.get_exploration_suggestions(
                player_pos, n=5
            )
            redirected = False
            for fr, fc in frontier:
                fkey = (
                    (fr // STEP_SIZE) * STEP_SIZE,
                    (fc // STEP_SIZE) * STEP_SIZE,
                )
                if self._navigate_failures.get(fkey, 0) >= self._NAVIGATE_BLACKLIST_THRESHOLD:
                    continue  # skip also-blacklisted frontiers
                alt_path = self.navigator.navigate_to(
                    fr, fc, player_pos[0], player_pos[1], max_steps=15,
                )
                if alt_path:
                    logger.info(
                        "navigate_to: BLACKLIST REDIRECT to frontier (%d,%d) "
                        "path=%s (%d steps)",
                        fr, fc, alt_path, len(alt_path),
                    )
                    # Execute the redirected path
                    target_r, target_c = fr, fc
                    target_key = fkey
                    # Fall through to path execution below
                    self._execute_navigate_path(
                        alt_path, target_r, target_c, player_pos,
                        STEP_SIZE, _DIR_DELTAS,
                    )
                    redirected = True
                    break
            if not redirected:
                # All frontiers also blacklisted or unreachable — try random unblocked
                qr = (player_pos[0] // STEP_SIZE) * STEP_SIZE
                qc = (player_pos[1] // STEP_SIZE) * STEP_SIZE
                for d in ["RIGHT", "LEFT", "DOWN", "UP"]:
                    if not self.navigator.memory.is_blocked((qr, qc), d):
                        fallback = self.navigator._dir_to_action.get(d)
                        if fallback:
                            logger.info(
                                "navigate_to: blacklist fallback -> %s (%s)",
                                fallback, d,
                            )
                            self._execute_single_action(fallback, "{}")
                            return
                # ACTION5 is a no-op in many games — just return instead
            return

        # Update navigator with latest action mappings
        self.navigator.update_action_mappings(self.perception._action_effects)

        # Compute BFS path
        path = self.navigator.navigate_to(
            target_r, target_c,
            player_pos[0], player_pos[1],
            max_steps=15,
        )

        if not path:
            # Record failure for blacklist tracking
            self._navigate_failures[target_key] = fail_count + 1
            logger.warning("navigate_to(%d,%d): no path found from (%d,%d) "
                          "(failure %d/%d)",
                          target_r, target_c, player_pos[0], player_pos[1],
                          fail_count + 1, self._NAVIGATE_BLACKLIST_THRESHOLD)

            # Force exploration: redirect to nearest unvisited frontier position
            frontier = self.navigator.get_exploration_suggestions(player_pos, n=5)
            for fr, fc in frontier:
                alt_path = self.navigator.navigate_to(
                    fr, fc, player_pos[0], player_pos[1], max_steps=15,
                )
                if alt_path:
                    logger.info("navigate_to: REDIRECTED to frontier (%d,%d) "
                               "path=%s (%d steps)",
                               fr, fc, alt_path, len(alt_path))
                    # Execute the redirected path (recurse with new target)
                    target_r, target_c = fr, fc
                    path = alt_path
                    break

        if not path:
            # Fallback: try an unblocked direction
            qr = (player_pos[0] // STEP_SIZE) * STEP_SIZE
            qc = (player_pos[1] // STEP_SIZE) * STEP_SIZE
            for d in ["RIGHT", "LEFT", "DOWN", "UP"]:
                if not self.navigator.memory.is_blocked((qr, qc), d):
                    fallback_action = self.navigator._dir_to_action.get(d)
                    if fallback_action:
                        logger.info("navigate_to: fallback -> %s (%s)", fallback_action, d)
                        self._execute_single_action(fallback_action, "{}")
                        return
            # All directions blocked — return and let the LLM decide
            logger.info("navigate_to: all directions blocked, returning to LLM")
            return

        logger.info("navigate_to(%d,%d): path=%s (%d steps) from player=(%d,%d)",
                    target_r, target_c, path, len(path),
                    player_pos[0], player_pos[1])

        self._execute_navigate_path(
            path, target_r, target_c, player_pos, STEP_SIZE, _DIR_DELTAS,
        )

        # Post-execution: check if agent actually reached the target.
        # If not (wall/teleport stopped us), count as a failure so the
        # blacklist catches targets that BFS can route to but execution
        # always fails on.
        final_pos = self._get_player_position()
        if final_pos:
            dist_r = abs(final_pos[0] - target_r)
            dist_c = abs(final_pos[1] - target_c)
            if dist_r > STEP_SIZE or dist_c > STEP_SIZE:
                self._navigate_failures[target_key] = (
                    self._navigate_failures.get(target_key, 0) + 1
                )
                logger.info(
                    "navigate_to(%d,%d): execution failed — ended at (%d,%d), "
                    "dist=(%d,%d). Failure %d/%d.",
                    target_r, target_c, final_pos[0], final_pos[1],
                    dist_r, dist_c,
                    self._navigate_failures[target_key],
                    self._NAVIGATE_BLACKLIST_THRESHOLD,
                )

    def _execute_navigate_path(
        self,
        path: list[str],
        target_r: int,
        target_c: int,
        player_pos: tuple[int, int],
        step_size: int,
        dir_deltas: dict,
    ) -> None:
        """Execute a navigate_to path, stopping on score/teleport/wall."""
        plan_start_score = self._last_score
        est_r, est_c = player_pos
        for i, action_name in enumerate(path):
            latest = self.frames[-1]
            if latest.state in (GameState.WIN, GameState.GAME_OVER):
                break
            if self.action_counter >= MAX_ACTIONS:
                logger.info("navigate_to: MAX_ACTIONS reached mid-path at step %d", i)
                break

            prev_pos = self._get_player_position()
            self._execute_single_action(action_name, "{}")
            curr_pos = self._get_player_position()

            # Update estimated position
            direction = self.navigator._action_to_dir.get(action_name)
            if direction and direction in dir_deltas:
                dr, dc = dir_deltas[direction]
                est_r += dr
                est_c += dc

            # Stop on score change
            if self._last_score != plan_start_score:
                logger.info("navigate_to: score changed at step %d, stopping", i + 1)
                break

            # Stop on no effect (wall hit) — navigator's wall info may be stale
            if self.current_steps and "no_change" in self.current_steps[-1].frame_diff:
                logger.info("navigate_to: wall hit at step %d at ~(%d,%d), stopping",
                           i + 1, est_r, est_c)
                break

            # Detect teleportation: player moved more than step_size in one step
            if prev_pos and curr_pos and prev_pos != curr_pos:
                teleport_dr = abs(curr_pos[0] - prev_pos[0])
                teleport_dc = abs(curr_pos[1] - prev_pos[1])
                if teleport_dr > step_size or teleport_dc > step_size:
                    # Record teleport trigger as a wall so BFS avoids it
                    if direction:
                        self.navigator.update_from_action_result(
                            player_pos=prev_pos, action=action_name,
                            moved=False, new_player_pos=None,
                        )
                        logger.info("navigate_to: TELEPORTATION at step %d: "
                                   "%s -> %s (delta=%d,%d), recorded wall %s going %s",
                                   i + 1, prev_pos, curr_pos, teleport_dr, teleport_dc,
                                   prev_pos, direction)
                    else:
                        logger.info("navigate_to: TELEPORTATION at step %d: "
                                   "%s -> %s (delta=%d,%d), stopping",
                                   i + 1, prev_pos, curr_pos, teleport_dr, teleport_dc)
                    # Teleport exploration DISABLED — costs 4 actions (18% of budget)
                    # per teleport with no demonstrated benefit. Let the LLM decide.
                    break

            # Stop if player didn't actually move (grid changed but player static)
            # Also record this as a wall so navigator avoids it next time
            if prev_pos and curr_pos and prev_pos == curr_pos:
                if direction:
                    self.navigator.update_from_action_result(
                        player_pos=prev_pos, action=action_name,
                        moved=False, new_player_pos=None,
                    )
                    logger.info("navigate_to: recorded wall at %s going %s", prev_pos, direction)
                logger.info("navigate_to: player didn't move at step %d (still at %s), stopping",
                           i + 1, curr_pos)
                break

        logger.info("navigate_to: finished at estimated pos (%d,%d)", est_r, est_c)

    # ------------------------------------------------------------------
    # Trigger detection helper
    # ------------------------------------------------------------------

    def _find_nearby_special_objects(
        self,
        grid: list[list[int]],
        player_pos: tuple[int, int],
        radius: int = 8,
    ) -> list[tuple[int, int, str, int]]:
        """Find special-shaped objects near the player.

        Only called when transformations are detected (rare), so the cost
        of a full grid analysis is acceptable.

        Returns:
            List of (center_r, center_c, shape, color) for objects within
            *radius* Manhattan distance of the player that have a special
            geometric shape (cross, diamond, T-shape, L-shape, U-shape).
        """
        from arc.game_intelligence import STEP_SIZE
        try:
            analysis = self.perception.analyze_grid(grid)
        except Exception:
            return []

        pr, pc = player_pos
        results: list[tuple[int, int, str, int]] = []

        special_shapes = {"cross", "diamond", "T-shape", "L-shape", "U-shape"}

        for obj in analysis.objects:
            if obj.shape not in special_shapes:
                continue
            dist = abs(int(obj.center_r) - pr) + abs(int(obj.center_c) - pc)
            if dist <= radius * STEP_SIZE:
                results.append((
                    int(obj.center_r),
                    int(obj.center_c),
                    obj.shape,
                    obj.color,
                ))

        # Also check composite shapes from clustering
        from arc.grid_perception import _cluster_nearby_objects
        try:
            composites = _cluster_nearby_objects(analysis.objects)
            for comp in composites:
                shape = comp.get("shape", "")
                if shape not in special_shapes:
                    continue
                cr, cc = comp.get("center", (0, 0))
                dist = abs(int(cr) - pr) + abs(int(cc) - pc)
                if dist <= radius * STEP_SIZE:
                    color = comp.get("color", 0)
                    results.append((int(cr), int(cc), shape, color))
        except Exception:
            pass  # composite clustering is optional

        return results

    # ------------------------------------------------------------------
    # LLM calls
    # ------------------------------------------------------------------

    _client: Optional[OpenAIClient] = None

    def _get_client(self) -> OpenAIClient:
        if self._client is None:
            logging.getLogger("openai").setLevel(logging.CRITICAL)
            logging.getLogger("httpx").setLevel(logging.CRITICAL)
            from arc.config import API_RETRIES, API_TIMEOUT, OPENROUTER_BASE_URL
            # Read API key at call time (not module-load time) because
            # arc/__init__.py imports config before __main__.py calls load_dotenv().
            api_key = (
                os.getenv("OPENROUTER_API_KEY")
                or os.getenv("OPENAI_API_KEY", "")
            )
            self._client = OpenAIClient(
                api_key=api_key,
                base_url=OPENROUTER_BASE_URL,
                timeout=API_TIMEOUT,
                max_retries=API_RETRIES,
            )
        return self._client

    def _llm_think_and_act(
        self, observation: str, latest: FrameData,
    ) -> tuple[Optional[tuple[str, str, str]], str]:
        """Single merged LLM call: reasoning + action in one round-trip.

        Returns (game_action_call_or_None, reasoning_text).
        """
        # 1. Push observation as tool result
        self.push_message({
            "role": "tool",
            "tool_call_id": self._latest_tool_call_id,
            "content": observation,
        })

        # 2. Build thinking pump prompt + grid image
        pump_prompt = self._build_thinking_pump_prompt()
        grid_image_b64 = self._render_frame_base64(latest)

        if grid_image_b64:
            self.push_message({
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{grid_image_b64}",
                        },
                    },
                    {"type": "text", "text": pump_prompt},
                ],
            })
        else:
            self.push_message({"role": "user", "content": pump_prompt})

        # 3. Single LLM call with tools
        client = self._get_client()
        tools = self.build_tools()
        reasoning = ""

        for _attempt in range(5):
            try:
                kwargs: dict[str, Any] = {
                    "model": self._model,
                    "messages": self._messages_for_api(game_context=self._game_context),
                    "tools": tools,
                    "tool_choice": "auto",
                }
                if self.REASONING_EFFORT is not None:
                    kwargs["reasoning_effort"] = self.REASONING_EFFORT
                if self._extra_body:
                    kwargs["extra_body"] = self._extra_body
                response = client.chat.completions.create(**kwargs)
            except (openai.BadRequestError, openai.APIError) as e:
                logger.warning("LLM think+act failed (%d/5): %s", _attempt + 1, e)
                time.sleep(5)
                continue

            self.track_tokens(response.usage.total_tokens)
            message = response.choices[0].message
            self.push_message(message)

            # Extract reasoning from content
            reasoning = message.content or ""
            if reasoning:
                # Strip accidental tool call XML
                import re as _re
                reasoning = _re.sub(
                    r'<tool_call>.*?</tool_call>', '', reasoning, flags=_re.DOTALL,
                ).strip()

            # Extract action from tool_calls
            if message.tool_calls:
                tool_calls = [
                    (tc.function.name, tc.function.arguments or "{}", tc.id)
                    for tc in message.tool_calls
                ]
                game_action = self._process_tool_calls(tool_calls)
                if game_action is not None:
                    # Update belief prediction for next pump
                    if reasoning:
                        self.autopilot.beliefs.last_prediction = reasoning[:200]
                    logger.info("LLM reasoning: %s", reasoning[:300])
                    return game_action, reasoning
                # Only notes were called, ask for action
                self.push_message({
                    "role": "user",
                    "content": "Good — knowledge saved. Now call a game action.",
                })
                continue

            # No tool calls — try parsing from text
            text_content = message.content or ""
            parsed = self._parse_tool_calls_from_text(text_content)
            if parsed:
                game_action = self._process_tool_calls(parsed)
                if game_action is not None:
                    return game_action, reasoning

            logger.warning(
                "LLM returned no tool calls (%d/5), text: %.300s",
                _attempt + 1, text_content.replace('\n', ' '),
            )
            self.push_message({
                "role": "user",
                "content": "Call exactly one of ACTION1-ACTION6 now.",
            })

        return None, reasoning

    def _build_thinking_pump_prompt(self) -> str:
        """Structured thinking prompt (Joycean Machine).

        Replaces separate observe + act prompts with a single structured prompt.
        """
        parts: list[str] = []
        beliefs = self.autopilot.beliefs

        # Pump 1: "What changed?" (prediction vs reality — Generate-and-Test)
        if self.current_steps:
            last = self.current_steps[-1]
            parts.append(
                "## What Changed?\n"
                f"Predicted: {beliefs.last_prediction or 'none'}\n"
                f"Actual: {last.action} -> {last.frame_diff}, "
                f"score {last.score_before}->{last.score_after}\n"
                "Was prediction correct? What does mismatch tell you?"
            )

        # Pump 2: Current beliefs
        parts.append(f"## Your Beliefs\n{beliefs.summarize()}")

        # Pump 3: Actions remaining (budget awareness)
        remaining = MAX_ACTIONS - len(self.current_steps)
        parts.append(f"## Budget: {remaining} actions left")

        # Pump 4: Failure analysis from previous retry (Rapoport's Rules)
        if beliefs.failure_analysis:
            parts.append(
                f"## LAST ATTEMPT ANALYSIS\n{beliefs.failure_analysis}"
            )

        # Pump 5: Joycean framing — explain to teammate, then act
        parts.append(
            "## Your Task\n"
            "1. What did you learn? Simplest explanation? (1-2 sentences)\n"
            "2. PREDICT what will happen with your next action\n"
            "3. Call exactly ONE of ACTION1-ACTION6\n"
        )
        return "\n\n".join(parts)

    @staticmethod
    def _parse_tool_calls_from_text(text: str) -> Optional[list[tuple[str, str, str]]]:
        """Parse tool calls embedded in text content (e.g. <tool_call> or <invoke> XML tags).

        Supports formats like:
          <tool_call><function=ACTION1></function></tool_call>
          <invoke name="ACTION1"><parameter name="actions">...</parameter></invoke>
          ACTION1  (bare action name on its own line)
        """
        import re
        import uuid

        results: list[tuple[str, str, str]] = []

        valid_actions = {"ACTION1", "ACTION2", "ACTION3", "ACTION4",
                         "ACTION5", "ACTION6", "update_game_notes"}

        # Pattern 1: <function=NAME> or <invoke name="NAME">
        for m in re.finditer(r'<(?:function=|invoke\s+name=["\'])(\w+)', text):
            name = m.group(1)
            if name in valid_actions:
                # Try to extract parameters/arguments
                args = "{}"
                # Look for <parameter name="...">...</parameter> after this match
                param_region = text[m.end():m.end() + 500]
                params = {}
                for pm in re.finditer(r'<parameter\s+name=["\'](\w+)["\']>(.*?)</parameter>', param_region, re.DOTALL):
                    params[pm.group(1)] = pm.group(2).strip()
                if params:
                    args = json.dumps(params)
                results.append((name, args, f"text_parsed_{uuid.uuid4().hex[:8]}"))

        if results:
            return results

        # Pattern 2: bare action name (e.g. "ACTION1" alone or "Next action: ACTION1")
        for m in re.finditer(r'\b(ACTION[1-6])\b', text):
            name = m.group(1)
            results.append((name, "{}", f"text_parsed_{uuid.uuid4().hex[:8]}"))
            break  # Only take the first one

        return results if results else None

    # ------------------------------------------------------------------
    # Hypothesis testing (Generate-and-Test / Boom Crutch)
    # ------------------------------------------------------------------

    def _run_hypothesis_test(self) -> Optional[str]:
        """Layer 2: return an action for hypothesis testing, or None."""
        beliefs = self.autopilot.beliefs
        if beliefs.phase != "hypothesis_testing":
            return None

        hyps = beliefs.hypotheses
        idx = beliefs.active_hypothesis_idx

        # Advance past tested hypotheses
        while idx < len(hyps) and hyps[idx].tested:
            idx += 1
        beliefs.active_hypothesis_idx = idx

        if idx >= len(hyps):
            # All hypotheses tested
            beliefs.phase = "exploring"
            return None

        h = hyps[idx]
        if h.target_pos is None:
            h.tested = True
            h.result = "UNREACHABLE"
            return self._run_hypothesis_test()

        player_pos = self._get_player_position()
        if not player_pos:
            return None

        # If autopilot has a current path for this hypothesis, use it
        if self.autopilot._current_path:
            action = self.autopilot._current_path.pop(0)
            beliefs.last_prediction = f"Hypothesis: {h.prediction}"
            return action

        # Compute BFS path to hypothesis target
        self.navigator.update_action_mappings(self.perception._action_effects)
        path = self.navigator.navigate_to(
            h.target_pos[0], h.target_pos[1],
            player_pos[0], player_pos[1],
            max_steps=15,
        )
        if path:
            self.autopilot._current_path = path[1:]
            self.autopilot._current_target = h.target_pos
            beliefs.last_prediction = f"Hypothesis: {h.prediction}"
            logger.info(
                "Hypothesis test: navigating to (%d,%d), path=%s",
                h.target_pos[0], h.target_pos[1], path,
            )
            return path[0]

        # Unreachable
        h.tested = True
        h.result = "UNREACHABLE"
        logger.info("Hypothesis target (%d,%d) unreachable", h.target_pos[0], h.target_pos[1])
        return self._run_hypothesis_test()

    def _evaluate_hypothesis(
        self,
        prev_grid: Optional[list[list[int]]],
        curr_grid: Optional[list[list[int]]],
        score_delta: int,
        prev_pos: Optional[tuple[int, int]],
        curr_pos: Optional[tuple[int, int]],
    ) -> None:
        """Evaluate whether the current hypothesis was confirmed/refuted."""
        beliefs = self.autopilot.beliefs
        idx = beliefs.active_hypothesis_idx
        if idx < 0 or idx >= len(beliefs.hypotheses):
            return

        h = beliefs.hypotheses[idx]
        if h.tested:
            return

        # Check if we reached the target
        from arc.game_intelligence import STEP_SIZE
        at_target = False
        if h.target_pos and curr_pos:
            dr = abs(curr_pos[0] - h.target_pos[0])
            dc = abs(curr_pos[1] - h.target_pos[1])
            at_target = dr <= STEP_SIZE and dc <= STEP_SIZE

        if not at_target:
            return  # Still en route

        # We're at the target — evaluate
        grid_changed = prev_grid != curr_grid if prev_grid and curr_grid else False

        if score_delta > 0:
            h.tested = True
            h.result = "CONFIRMED"
            beliefs.confirmed_rules.append(h.prediction)
            logger.info("Hypothesis CONFIRMED (score +%d): %s", score_delta, h.prediction)
        elif grid_changed:
            h.tested = True
            h.result = "PARTIALLY_CONFIRMED"
            logger.info("Hypothesis PARTIALLY CONFIRMED (grid changed): %s", h.prediction)
        else:
            h.tested = True
            h.result = "REFUTED"
            logger.info("Hypothesis REFUTED: %s", h.prediction)

    # ------------------------------------------------------------------
    # Charitable failure analysis (Rapoport's Rules)
    # ------------------------------------------------------------------

    def _charitable_failure_analysis(self) -> str:
        """Analyze what worked and what didn't at episode end.

        Rapoport's Rules: charitable interpretation before abandoning strategies.
        """
        if not self.current_steps:
            return ""

        parts: list[str] = []
        score = self._last_score

        # 1. What DID work?
        score_events = [
            s for s in self.current_steps
            if s.score_after > s.score_before
        ]
        if score_events:
            event_descs = [
                f"Step {i}: {s.action} scored (score {s.score_before}->{s.score_after})"
                for i, s in enumerate(self.current_steps)
                if s.score_after > s.score_before
            ]
            parts.append(f"WORKED: {'; '.join(event_descs[:3])}")

        # Grid changes (meaningful actions)
        grid_change_count = sum(
            1 for s in self.current_steps if s.frame_diff == "grid_changed"
        )
        wall_hit_count = sum(
            1 for s in self.current_steps if s.frame_diff == "no_change"
        )
        parts.append(
            f"Stats: {grid_change_count} effective moves, "
            f"{wall_hit_count} wall hits, score={score}"
        )

        # 2. Where did we get stuck?
        if score == 0:
            # Find first long no-score streak
            streak_start = 0
            for i, s in enumerate(self.current_steps):
                if i > 5 and all(
                    self.current_steps[j].score_after == self.current_steps[j].score_before
                    for j in range(max(0, i - 5), i + 1)
                ):
                    streak_start = i - 5
                    break
            if streak_start > 0:
                stuck_actions = [
                    self.current_steps[j].action
                    for j in range(streak_start, min(streak_start + 5, len(self.current_steps)))
                ]
                parts.append(
                    f"STUCK at step ~{streak_start}: actions {', '.join(stuck_actions)}"
                )

        # 3. Charitable interpretation
        if wall_hit_count > grid_change_count:
            parts.append(
                "ANALYSIS: Too many wall hits — navigation was wrong. "
                "Try different routes or unexplored areas."
            )
        elif score == 0 and grid_change_count > 5:
            parts.append(
                "ANALYSIS: Many moves but no score — interacting with "
                "wrong objects or missing prerequisites."
            )

        # 4. AutoPilot beliefs summary
        beliefs = self.autopilot.beliefs
        if beliefs.confirmed_rules:
            parts.append(f"CONFIRMED: {'; '.join(beliefs.confirmed_rules[-3:])}")

        hypothesis_results = {}
        for h in beliefs.hypotheses:
            if h.tested:
                hypothesis_results[h.result] = hypothesis_results.get(h.result, 0) + 1
        if hypothesis_results:
            results_str = ", ".join(
                f"{k}: {v}" for k, v in hypothesis_results.items()
            )
            parts.append(f"Hypotheses: {results_str}")

        # 5. Concrete recommendation
        if score == 0:
            parts.append(
                "RECOMMENDATION: Try exploring areas NOT visited in this attempt. "
                "Test ACTION5/ACTION6 on special objects."
            )
        else:
            parts.append(
                f"RECOMMENDATION: Score reached {score}. "
                "Repeat the scoring actions faster, then explore further."
            )

        return " | ".join(parts)

    # ------------------------------------------------------------------
    # Level completion summary
    # ------------------------------------------------------------------

    def _summarize_level_completion(self, prev_score: int, curr_score: int) -> None:
        """After clearing a level, ask LLM to summarize what worked and write to SKILL.md."""
        level_num = curr_score
        n_steps = len(self.current_steps)

        # Build a concise history of recent actions leading to the score
        recent_steps = self.current_steps[-30:]  # last 30 steps for context
        step_log = "\n".join(
            f"  Step {n_steps - len(recent_steps) + i + 1}: {s.action} -> {s.frame_diff} (score {s.score_before}->{s.score_after})"
            for i, s in enumerate(recent_steps)
        )

        # Collect known game notes from SKILL.md
        known_notes = ""
        try:
            known_notes = self.skill_path.read_text(encoding="utf-8")
            # Extract just the "Discovered Knowledge" section
            marker = "## Discovered Knowledge"
            idx = known_notes.find(marker)
            if idx >= 0:
                known_notes = known_notes[idx:]
        except Exception:
            pass

        # Gather rich game intelligence context
        game_context_parts: list[str] = []

        # Action mappings
        action_effects = self.perception._action_effects
        if action_effects:
            mappings = ", ".join(
                f"{a}={d}" for a, d in sorted(action_effects.items())
            )
            game_context_parts.append(f"Action mappings: {mappings}")

        # Player position
        player_pos = self._get_player_position()
        if player_pos:
            game_context_parts.append(
                f"Player position at score: ({player_pos[0]},{player_pos[1]})"
            )

        # Interaction rules learned
        rules_text = self.interaction_tracker.get_rules_summary()
        if rules_text:
            game_context_parts.append(f"Interaction rules:\n{rules_text}")

        # Trigger hypotheses
        trigger_text = self.interaction_tracker.get_trigger_hypotheses_summary()
        if trigger_text:
            game_context_parts.append(trigger_text)

        # Transformation events this episode
        transform_events = self.transformation_detector._history
        if transform_events:
            recent_transforms = transform_events[-10:]
            t_lines = [
                f"  Step {e.step}: {e.description}"
                for e in recent_transforms
            ]
            game_context_parts.append(
                "Transformations detected:\n" + "\n".join(t_lines)
            )

        # Object inventory summary
        inv_text = self.inventory.get_inventory_summary()
        if inv_text:
            game_context_parts.append(f"Objects seen:\n{inv_text[:500]}")

        game_context = "\n\n".join(game_context_parts) if game_context_parts else "No game intelligence data."

        prompt = (
            f"You just completed Level {level_num} of the game (score went from {prev_score} to {curr_score}).\n"
            f"Total actions this episode: {n_steps}.\n\n"
            f"Game intelligence:\n{game_context}\n\n"
            f"Recent action log:\n{step_log}\n\n"
            f"Current knowledge:\n{known_notes[:1000]}\n\n"
            "Write a CONCISE summary (under 200 words, NO thinking/reasoning process) of HOW you cleared this level:\n"
            "1. **Key mechanics**: Movement rules, object interactions, teleportation, triggers\n"
            "2. **Winning sequence**: The specific actions/positions that triggered the score\n"
            "3. **Mistakes to avoid**: Wasted actions or wrong approaches\n"
            "4. **Strategy for next level**: What to do first based on what you learned\n\n"
            "Be specific with coordinates, colors, and action names. Output ONLY the summary, no reasoning."
        )

        client = self._get_client()
        try:
            create_kwargs: dict[str, Any] = {
                "model": self._model,
                "messages": [{"role": "user", "content": prompt}],
            }
            if self._extra_body:
                create_kwargs["extra_body"] = self._extra_body
            response = client.chat.completions.create(**create_kwargs)
            summary = response.choices[0].message.content or ""
            self.track_tokens(response.usage.total_tokens, summary)
        except Exception as e:
            logger.warning("Level summary LLM call failed: %s", e)
            summary = f"Level {level_num} cleared in {n_steps} steps."

        if not summary.strip():
            summary = f"Level {level_num} cleared in {n_steps} steps."

        # Write to SKILL.md under level_strategies
        level_note = f"Level {level_num} Summary (auto):\n{summary.strip()}"
        result = handle_game_notes_update(
            json.dumps({"section": "level_strategies", "content": level_note}),
            self.skill_path,
            score=curr_score,
            trigger="level_summary",
        )
        logger.info(
            "Level %d complete! Summary written to SKILL.md: %s",
            level_num, result[:100],
        )
        logger.info("Level %d summary: %s", level_num, summary[:500])

    # ------------------------------------------------------------------
    # Grid image rendering
    # ------------------------------------------------------------------

    def _render_frame_base64(self, latest: FrameData) -> Optional[str]:
        """Render current frame as a base64 PNG string for vision input."""
        try:
            frame = latest.frame
            if not frame:
                return None
            img = self.perception.render_frame(frame, scale=8, show_labels=True)
            if img is None:
                return None
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception as e:
            logger.warning("Failed to render frame image: %s", e)
            return None

    # ------------------------------------------------------------------
    # Observation prompt construction
    # ------------------------------------------------------------------

    def _build_observation(self, latest: FrameData) -> str:
        # Consume the one-shot causal alert if present
        causal_alert = self._trigger_causal_alert
        self._trigger_causal_alert = ""

        # Filter hypotheses: mark those targeting blacklisted/exhausted regions
        hyp_text = self._hypotheses_text
        if self._hypotheses and (self._navigate_failures or self._region_visits):
            from arc.game_intelligence import STEP_SIZE
            active_hyps = []
            for h in self._hypotheses:
                # Extract row/col from test_action like "Move toward (32,21) ..."
                import re
                m = re.search(r"\((\d+),\s*(\d+)\)", h.test_action)
                if m:
                    hr = (int(m.group(1)) // STEP_SIZE) * STEP_SIZE
                    hc = (int(m.group(2)) // STEP_SIZE) * STEP_SIZE
                    hkey = (hr, hc)
                    if (self._navigate_failures.get(hkey, 0)
                            >= self._NAVIGATE_BLACKLIST_THRESHOLD):
                        continue  # skip blacklisted
                    if (self._region_visits.get(hkey, 0)
                            >= self._REGION_VISIT_LIMIT
                            and self._last_score
                            <= self._region_last_score.get(hkey, 0)):
                        continue  # skip exhausted
                active_hyps.append(h)
            if len(active_hyps) < len(self._hypotheses):
                hyp_text = HypothesisEngine.format_hypotheses(active_hyps)

        # Append reachability info to first-look analysis for early steps
        first_look = self._first_look_analysis
        reachability = getattr(self, "_reachability_info", "")
        if reachability and first_look:
            first_look = first_look + "\n\n" + reachability
        elif reachability:
            first_look = reachability

        return build_func_resp_prompt(
            latest_frame=latest,
            frames=self.frames,
            perception=self.perception,
            last_action_name=self.last_action_name,
            retry_count=self.retry_count,
            max_retries=None,
            interaction_tracker=self.interaction_tracker,
            transformation_detector=self.transformation_detector,
            inventory=self.inventory,
            navigator=self.navigator,
            get_player_position=self._get_player_position,
            build_buffer_context=self._build_buffer_context,
            build_action_history=self._build_action_history,
            build_loop_warning=self._build_loop_warning,
            build_stuck_warning=self._build_stuck_warning,
            current_steps=self.current_steps,
            trigger_causal_alert=causal_alert,
            first_look_analysis=first_look,
            region_similarities=self._region_similarities,
            hypotheses_text=hyp_text,
            belief_summary=self.autopilot.beliefs.summarize(),
            failure_analysis=self.autopilot.beliefs.failure_analysis,
        )

    # ------------------------------------------------------------------
    # Helper methods (passed as callbacks to prompts.build_func_resp_prompt)
    # ------------------------------------------------------------------

    def _get_player_position(self) -> Optional[tuple[int, int]]:
        if self.perception._player_obj is not None:
            obj = self.perception._player_obj
            return (int(obj.center_r), int(obj.center_c))
        return None

    def _build_buffer_context(self) -> str:
        """Format episode buffer context for the prompt."""
        if self.episode_buffer.get_size() == 0:
            return ""

        ctx_parts = [f"game:{self.game_id}", f"actions:{len(self.current_steps)}"]
        if self.current_steps:
            recent = " ".join(s.action for s in self.current_steps[-10:])
            ctx_parts.append(f"recent:{recent}")
        query_emb = self.embedder.encode(" ".join(ctx_parts))

        results = self.episode_buffer.retrieve(
            query_emb, k=NUM_RETRIEVE, game_id=self.game_id,
        )
        if not results:
            return ""

        parts = ["# EPISODE BUFFER (past attempts)"]
        for ep, sim in results:
            parts.append(ep.summary(max_steps=6))
        return "\n".join(parts)

    def _build_action_history(self) -> str:
        """Format recent action history."""
        analysis = self.loop_detector.analyze(self.current_steps)
        if analysis.recent_action_summary:
            return f"# RECENT ACTIONS\n{analysis.recent_action_summary}"
        return ""

    def _build_loop_warning(self) -> str:
        """Warn if repetitive action cycles detected."""
        analysis = self.loop_detector.analyze(self.current_steps)
        if analysis.is_looping:
            cycle = ",".join(analysis.cycle_actions)
            return (
                f"# WARNING: LOOP DETECTED\n"
                f"Pattern: {cycle} (repeated {analysis.cycle_repetitions}x)\n"
                f"STOP repeating this pattern. Try a COMPLETELY different approach."
            )
        return ""

    def _build_stuck_warning(self) -> str:
        """Warn if no score change for many steps, with exploration suggestions."""
        analysis = self.loop_detector.analyze(self.current_steps)

        # Always include blacklisted + exhausted targets if any
        blacklisted = [
            (r, c) for (r, c), n in self._navigate_failures.items()
            if n >= self._NAVIGATE_BLACKLIST_THRESHOLD
        ]
        exhausted = [
            (r, c) for (r, c), n in self._region_visits.items()
            if n >= self._REGION_VISIT_LIMIT
            and self._last_score <= self._region_last_score.get((r, c), 0)
        ]
        blocked_targets = list(set(blacklisted + exhausted))
        bl_text = ""
        if blocked_targets:
            targets = ", ".join(f"({r},{c})" for r, c in sorted(blocked_targets))
            bl_text = (
                f"\n# BLOCKED TARGETS (do NOT move toward these): {targets}"
                f"\nThese areas have been visited too many times without progress."
                f"\nPick a COMPLETELY DIFFERENT area of the grid."
            )

        if analysis.is_stuck:
            parts = [
                f"# WARNING: STUCK "
                f"({analysis.steps_since_score_change} steps since score change)"
            ]

            # PRIORITY 1: Suggest unvisited objects from inventory
            from arc.game_intelligence import ObjectStatus
            active_objects = [
                item for item in self.inventory._items
                if item.status not in (ObjectStatus.COLLECTED, ObjectStatus.VISITED)
            ]
            if active_objects:
                active_objects.sort(key=lambda i: i.distance_actions)
                parts.append(
                    f"INTERACT WITH OBJECTS — you have {len(active_objects)} "
                    f"objects you haven't stepped on yet!"
                )
                parts.append(
                    "Do NOT wander to empty areas. Go DIRECTLY to these objects:"
                )
                for item in active_objects[:3]:
                    shape_tag = ""
                    if item.shape in ("cross", "diamond", "T-shape", "L-shape", "U-shape"):
                        shape_tag = f" **{item.shape.upper()}**"
                    parts.append(
                        f"  -> color {item.color}{shape_tag} at "
                        f"({item.position[0]},{item.position[1]}) "
                        f"[{item.role}] ~{item.distance_actions:.0f} steps"
                    )
                best = active_objects[0]
                parts.append(
                    f"TARGET: ({best.position[0]},{best.position[1]}) — move toward it using ACTION1-ACTION4"
                )
            else:
                # PRIORITY 2: Frontier exploration (only when no objects available)
                player_pos = self._get_player_position()
                frontier = self.navigator.get_exploration_suggestions(player_pos, n=3)
                if frontier:
                    frontier = [
                        (r, c) for r, c in frontier
                        if self._navigate_failures.get((r, c), 0)
                        < self._NAVIGATE_BLACKLIST_THRESHOLD
                    ]
                if frontier:
                    parts.append(
                        "No unvisited objects found. EXPLORE NEW AREAS:"
                    )
                    suggestions = ", ".join(
                        f"({r},{c})" for r, c in frontier
                    )
                    parts.append(f"Unvisited positions nearby: {suggestions}")
                    parts.append(
                        f"Move toward ({frontier[0][0]},{frontier[0][1]}) using ACTION1-ACTION4."
                    )
                else:
                    parts.append("Try a completely different direction or strategy.")
            return "\n".join(parts) + bl_text
        if analysis.no_effect_actions:
            blocked = ", ".join(
                f"{a} ({n}x)" for a, n in analysis.no_effect_actions.items()
            )
            return f"# Actions with no effect recently: {blocked}" + bl_text
        return bl_text

    # ------------------------------------------------------------------
    # Memento-S: semantic routing context
    # ------------------------------------------------------------------

    def _update_game_context(self) -> None:
        """Build game context string for semantic skill routing each turn."""
        loop_analysis = self.loop_detector.analyze(self.current_steps)

        # Determine game phase
        n_steps = len(self.current_steps)
        if n_steps < 5:
            phase = "exploring"
        elif self._last_score > 0:
            phase = "progressing"
        else:
            phase = "searching"

        # Determine score change
        score_changed = False
        if len(self.current_steps) >= 2:
            last = self.current_steps[-1]
            score_changed = last.score_after > last.score_before

        # Nearby objects from latest grid perception
        objects_nearby: list[str] = []
        if self.frames:
            latest_grid = self.frames[-1].frame[0] if self.frames[-1].frame else None
            if latest_grid:
                try:
                    analysis = self.perception.analyze_grid(latest_grid)
                    objects_nearby = [
                        str(obj.color) for obj in analysis.objects[:5]
                    ]
                except Exception:
                    pass

        self._game_context = SkillRouter.build_game_context(
            game_phase=phase,
            last_action=self.last_action_name,
            action_had_effect=(
                bool(self.current_steps)
                and self.current_steps[-1].frame_diff != "no_change"
            ),
            score_changed=score_changed,
            is_stuck=loop_analysis.is_stuck,
            is_looping=loop_analysis.is_looping,
            is_game_over=False,  # we check before calling this
            is_new_level=score_changed and self._last_score > 0,
            has_action_mappings=bool(self.perception._action_effects),
            objects_nearby=objects_nearby,
            retry_count=self.retry_count,
        )

    # ------------------------------------------------------------------
    # Episode management
    # ------------------------------------------------------------------

    def _finalize_episode(self, success: bool) -> None:
        """Save episode to buffer and (if successful) save replay."""
        score = self._frame_score(self.frames[-1])
        ctx_parts = [
            f"game:{self.game_id}",
            f"actions:{len(self.current_steps)}",
            f"score:{score}",
        ]
        if self.current_steps:
            recent = " ".join(s.action for s in self.current_steps[-10:])
            ctx_parts.append(f"recent:{recent}")
        ctx_text = " ".join(ctx_parts)

        episode = GameEpisode(
            game_id=self.game_id,
            steps=list(self.current_steps),
            success=success,
            final_score=score,
            total_actions=len(self.current_steps),
            embedding=self.embedder.encode(ctx_text),
            step_embeddings=list(self.current_step_embeddings),
        )
        self.episode_buffer.add(episode)
        self.embedder.add_document(ctx_text)

        if success:
            actions = [s.action for s in self.current_steps]
            save_level_replay(self.game_id, score, actions, CHECKPOINT_DIR)

        logger.info(
            "Episode done: %s, score=%d, actions=%d, buffer_size=%d",
            "SUCCESS" if success else "FAILED",
            score,
            len(self.current_steps),
            self.episode_buffer.get_size(),
        )

    def _reset_for_retry(self) -> None:
        """Reset per-episode state for a new attempt.

        Preserves cross-episode knowledge:
        - Navigator wall map (same game = same walls)
        - Action mappings (same game = same controls)
        - Interaction rules and trigger patterns
        - Color classifications
        - AutoPilot beliefs (action map, confirmed rules, failure analysis)
        """
        # Charitable failure analysis (Rapoport's Rules) before reset
        failure_analysis = self._charitable_failure_analysis()
        logger.info("Failure analysis: %s", failure_analysis[:300])

        self.current_steps = []
        self.current_step_embeddings = []
        # Keep action effects — same game mechanics across episodes
        saved_action_effects = dict(self.perception._action_effects)
        self.perception.reset()
        self.perception._action_effects = saved_action_effects
        # Soft reset: keep wall memory across retries
        self.navigator.soft_reset()
        self.interaction_tracker.reset()
        self.inventory.reset()
        self.transformation_detector.reset()
        self.loop_detector.reset()
        self._last_score = 0
        self.action_counter = 0
        self._trigger_causal_alert = ""
        # Keep all navigate failures — same game = same walls.
        # No decay: targets that failed once will stay blacklisted.
        # (wall map persists across retries, so re-trying wastes actions)
        # Persist region visits across retries (decay by half).
        self._region_visits = {
            k: max(0, v - v // 2) for k, v in self._region_visits.items() if v > 1
        }
        # Region scores reset since score resets on RESET
        self._region_last_score.clear()
        # Reset first-look (will be regenerated on next episode)
        self._first_look_analysis = ""
        self._region_similarities = ""
        self._hypotheses = []
        self._hypotheses_text = ""
        self._reachability_info = ""

        # Reset AutoPilot with preserved beliefs
        self.autopilot.reset_episode(keep_beliefs=True)
        self.autopilot.beliefs.failure_analysis = failure_analysis

    # ------------------------------------------------------------------
    # Checkpoint
    # ------------------------------------------------------------------

    def _try_load_checkpoint(self) -> None:
        result = load_checkpoint(
            self.game_id,
            self.episode_buffer,
            self.embedder,
            self.perception._action_effects,
            CHECKPOINT_DIR,
        )
        if result:
            self.retry_count = result["retry_count"]
            self.total_reasoning_tokens = result["total_reasoning_tokens"]
            self.token_counter = result["token_counter"]
            logger.info("Loaded checkpoint: retry=%d", self.retry_count)

    def _save_checkpoint(self) -> None:
        save_checkpoint(
            self.game_id,
            self.retry_count,
            self.total_reasoning_tokens,
            self.token_counter,
            self.episode_buffer,
            self.current_steps,
            self.current_step_embeddings,
            self.embedder,
            self.perception._action_effects,
            CHECKPOINT_DIR,
        )

    # ------------------------------------------------------------------
    # Live video generation
    # ------------------------------------------------------------------

    def _generate_live_video(self) -> None:
        """Generate MP4 from current recording, overwriting previous."""
        if not hasattr(self, "recorder") or not self.recorder.filename:
            return
        try:
            import importlib.util
            _viz_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts", "visualize_recording.py")
            spec = importlib.util.spec_from_file_location("visualize_recording", _viz_path)
            viz = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(viz)
            build_mp4, load_events = viz.build_mp4, viz.load_events
            rec_path = self.recorder.filename
            events = load_events(rec_path)
            if not events:
                return
            rec_dir = os.path.dirname(rec_path) or "recordings"
            # Name: {game_id}.{model}.{start_ts}_live.mp4
            model_tag = self._model.replace("/", "-").replace(":", "-")
            start_ts = self.recorder.start_ts if hasattr(self.recorder, "start_ts") else ""
            mp4_path = os.path.join(rec_dir, f"{self.game_id}.{model_tag}.{start_ts}_live.mp4")
            build_mp4(events, mp4_path, fps=2.5)
            logger.info("Live video updated: %s (%d frames)", mp4_path, len(events))
        except Exception as e:
            logger.debug("Live video generation skipped: %s", e)

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _frame_score(frame: FrameData) -> int:
        return getattr(frame, "score", frame.levels_completed)

    def is_done(self, frames: list[FrameData], latest_frame: FrameData) -> bool:
        # Not used directly (main() is overridden), but required by ABC.
        return latest_frame.state is GameState.WIN

    def choose_action(self, frames: list[FrameData], latest_frame: FrameData) -> GameAction:
        # Not used directly (main() is overridden), but required by ABC.
        raise NotImplementedError("ReactBufferAgent uses main() directly")
