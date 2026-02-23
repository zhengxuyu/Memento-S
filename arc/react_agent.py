"""ReactAgent: Minimal LLM-driven agent for ARC-AGI-3.

No built-in game strategies, no autopilot, no hypothesis engine.
The agent discovers everything through:
  1. Raw observation (grid state, score, action effects)
  2. LLM reasoning (observe → think → act)
  3. Persistent skill notes (update_game_notes writes to SKILL.md)

The agent is meant to learn purely through skill acquisition and creation.
"""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Optional

import openai
from arcengine import FrameData, GameAction, GameState
from openai import OpenAI as OpenAIClient

from arc.config import (
    MAX_ACTIONS,
    MAX_RETRIES,
    MESSAGE_LIMIT,
    SKILLS_DIR,
    API_RETRIES,
)
from arc.llm_agent import LLM
from arc.prompts import build_func_resp_prompt, build_user_prompt
from arc.tools import build_react_tools, handle_game_notes_update

logger = logging.getLogger(__name__)


class ReactAgent(LLM):
    """Minimal ReAct agent — LLM + raw game state, no programmatic help."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        # Episode state
        self.current_steps: list[dict] = []
        self.retry_count: int = 0
        self._last_score: int = 0

        # Skill file for persistent knowledge
        self.skill_path = Path(SKILLS_DIR) / "arc_game_playing" / "SKILL.md"
        self._ensure_skill_file()

    def _ensure_skill_file(self) -> None:
        """Create SKILL.md from template if it doesn't exist."""
        if self.skill_path.exists():
            return
        template = self.skill_path.parent / "SKILL.template.md"
        if template.exists():
            import shutil
            self.skill_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(template, self.skill_path)
        else:
            # Create a minimal skill file
            self.skill_path.parent.mkdir(parents=True, exist_ok=True)
            self.skill_path.write_text(
                "# ARC Game Notes\n\n"
                "### Action Mappings\n\n"
                "### Game Rules\n\n"
                "### Level Strategies\n\n"
                "### Object Roles\n\n"
                "### Tips\n",
                encoding="utf-8",
            )

    # ------------------------------------------------------------------
    # Main loop — retry on failure
    # ------------------------------------------------------------------

    def main(self) -> None:
        self.timer = time.time()

        while True:
            result = self._play_episode()

            if result == "win":
                logger.info(
                    "WIN on attempt %d! Total actions: %d, time: %.1fs",
                    self.retry_count + 1, self.action_counter, self.seconds,
                )
                break
            elif result in ("game_over", "max_actions"):
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
    # Play one episode
    # ------------------------------------------------------------------

    def _play_episode(self) -> str:
        """Play one episode. Returns 'win', 'game_over', or 'max_actions'."""
        # Reset game
        frame = self.take_action(GameAction.RESET)
        if frame:
            self.append_frame(frame)
        self.last_action_name = "RESET"
        self._last_score = self._frame_score(self.frames[-1])

        # Init conversation
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
                return "win"
            if latest.state is GameState.GAME_OVER:
                return "game_over"
            if self.action_counter >= MAX_ACTIONS:
                logger.info("Max actions (%d) reached", MAX_ACTIONS)
                return "max_actions"

            # Build observation
            obs = self._build_observation(latest)

            # LLM call → action
            action_result = self._llm_step(obs)
            if action_result:
                tc_name, tc_args, tc_id = action_result
                self._latest_tool_call_id = tc_id
                self._execute_action(tc_name, tc_args)
            else:
                logger.warning("LLM failed to produce action, skipping turn")
                self._latest_tool_call_id = f"skip_{self.action_counter}"

            step_count += 1

    # ------------------------------------------------------------------
    # Observation
    # ------------------------------------------------------------------

    def _build_observation(self, latest: FrameData) -> str:
        """Build observation prompt — raw game state only."""
        action_history = self._build_action_history()
        return build_func_resp_prompt(
            latest_frame=latest,
            frames=self.frames,
            last_action_name=getattr(self, "last_action_name", ""),
            retry_count=self.retry_count,
            current_steps=self.current_steps,
            max_retries=MAX_RETRIES,
            action_history=action_history,
        )

    def _build_action_history(self, n: int = 10) -> str:
        """Last N actions and their effects."""
        if not self.current_steps:
            return ""
        recent = self.current_steps[-n:]
        lines = ["# Recent Actions:"]
        for i, step in enumerate(recent):
            lines.append(f"  {i+1}. {step.get('action', '?')} -> {step.get('effect', '?')}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # LLM call
    # ------------------------------------------------------------------

    def _llm_step(self, observation: str) -> Optional[tuple[str, str, str]]:
        """Single LLM call: observation → action.

        Returns (tool_name, tool_args_json, tool_call_id) or None.
        """
        # Push observation as tool response
        self.push_message({
            "role": "tool",
            "tool_call_id": self._latest_tool_call_id,
            "content": observation,
        })

        from arc.config import OPENROUTER_BASE_URL
        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY", "")
        client = OpenAIClient(api_key=api_key, base_url=OPENROUTER_BASE_URL)

        tools = self._build_tools()

        for attempt in range(API_RETRIES):
            try:
                create_kwargs: dict[str, Any] = {
                    "model": self._model,
                    "messages": self._messages_for_api(),
                    "tools": tools,
                    "tool_choice": "required",
                }
                extra = self._extra_body
                if extra:
                    create_kwargs["extra_body"] = extra

                response = client.chat.completions.create(**create_kwargs)
                break
            except openai.BadRequestError:
                logger.warning("BadRequestError on attempt %d", attempt + 1)
                if attempt == API_RETRIES - 1:
                    return None
            except (openai.APIConnectionError, openai.RateLimitError, openai.APITimeoutError) as e:
                logger.warning("API error on attempt %d: %s", attempt + 1, e)
                if attempt == API_RETRIES - 1:
                    return None
                time.sleep(2 ** attempt)
        else:
            return None

        self.track_tokens(response.usage.total_tokens if response.usage else 0)
        message = response.choices[0].message

        # Extract reasoning
        reasoning = message.content or ""
        if reasoning:
            logger.info("LLM reasoning: %s", reasoning[:200])

        # Process tool calls — handle update_game_notes, return game action
        if message.tool_calls:
            game_action_call = None
            for tc in message.tool_calls:
                if tc.function.name == "update_game_notes":
                    # Execute notes update inline
                    result = handle_game_notes_update(
                        tc.function.arguments,
                        self.skill_path,
                        score=self._last_score,
                    )
                    logger.info("Game notes updated: %s", result)
                    # Push tool response so conversation stays valid
                    self.push_message(message)
                    self.push_message({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    })
                    # Need another LLM call to get the actual game action
                    return self._llm_step("")
                else:
                    game_action_call = tc

            if game_action_call:
                self.push_message(message)
                return (
                    game_action_call.function.name,
                    game_action_call.function.arguments or "{}",
                    game_action_call.id,
                )

        # Fallback: no tool calls
        if message.content:
            self.push_message({"role": "assistant", "content": message.content})
        return None

    def _build_tools(self) -> list[dict[str, Any]]:
        """Build tool list: ACTION1-6 + update_game_notes."""
        base_functions = self.build_functions()
        extended = build_react_tools(base_functions)
        return [
            {
                "type": "function",
                "function": {
                    "name": f["name"],
                    "description": f["description"],
                    "parameters": f.get("parameters", {}),
                    "strict": True,
                },
            }
            for f in extended
        ]

    # ------------------------------------------------------------------
    # Action execution
    # ------------------------------------------------------------------

    def _execute_action(self, name: str, args_json: str) -> None:
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
        self._last_score = curr_score

        # Determine effect
        if prev_grid and curr_grid:
            effect = "grid_changed" if prev_grid != curr_grid else "no_change"
        else:
            effect = "unknown"

        score_delta = curr_score - prev_score
        if score_delta > 0:
            effect += f" +{score_delta} score"

        # Record step
        self.current_steps.append({
            "action": name,
            "effect": effect,
            "score": curr_score,
        })

        logger.info(
            "%s: %s -> %s (score %d->%d, action #%d)",
            self.game_id, name, effect, prev_score, curr_score, self.action_counter,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _frame_score(self, frame: FrameData) -> int:
        return getattr(frame, "score", 0) or frame.levels_completed or 0

    def _reset_for_retry(self) -> None:
        """Reset state for a new attempt, keeping learned knowledge in SKILL.md."""
        self.current_steps = []
        self.action_counter = 0
        self._last_score = 0
        # Messages reset happens in _play_episode

    def _generate_live_video(self) -> None:
        """Generate a live video of the current recording."""
        if not hasattr(self, "recorder") or not self.recorder.filename:
            return
        try:
            import importlib.util
            viz_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "scripts", "visualize_recording.py",
            )
            if not os.path.exists(viz_path):
                return
            spec = importlib.util.spec_from_file_location("visualize_recording", viz_path)
            viz = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(viz)

            rec_path = self.recorder.filename
            events = viz.load_events(rec_path)
            if not events:
                return

            mp4_path = rec_path.rsplit(".", 1)[0] + "_live.mp4"
            viz.build_mp4(events, mp4_path, fps=5)
        except Exception as e:
            logger.debug("Live video generation failed: %s", e)
