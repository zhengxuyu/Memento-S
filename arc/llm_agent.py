"""LLM agent mixin for OpenAI-compatible tool-calling."""
import json
import logging
import os
import textwrap
from pathlib import Path
from typing import Any, Optional

import openai
from arcengine import FrameData, GameAction, GameState
from openai import OpenAI as OpenAIClient

from arc.agent_base import Agent

logger = logging.getLogger()


class LLM(Agent):
    """An agent that uses a base LLM model to play games."""

    MAX_ACTIONS: int = 80
    DO_OBSERVATION: bool = True
    REASONING_EFFORT: Optional[str] = None
    MODEL_REQUIRES_TOOLS: bool = False
    MESSAGE_LIMIT: int = 10
    MODEL: str = "openai/gpt-5.4-mini"
    messages: list[dict[str, Any]]
    token_counter: int

    _latest_tool_call_id: str = "call_12345"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.messages = []
        self.token_counter = 0
        self._skills_system_prompt = None
        self._history_summary: str = ""  # rolling summary of truncated history

    @property
    def _model(self) -> str:
        return os.environ.get("ARC_AGI_MODEL", "").strip() or self.MODEL

    @property
    def _extra_body(self) -> dict[str, Any] | None:
        body: dict[str, Any] = {}
        provider = os.environ.get("OPENROUTER_PROVIDER", "").strip()
        if provider:
            body["provider"] = {"order": [provider]}
        # Request reasoning/thinking from models that support it (not GPT)
        if not self._model.startswith("openai/"):
            body["include_reasoning"] = True
        return body or None

    def _get_system_prompt(self) -> str:
        """Build system prompt with ARC game context and any loaded skills."""
        sections: list[str] = []

        # Core ARC game context
        sections.append(
            "# ARC-AGI-3 Game\n\n"
            "Unknown grid game. Discover rules by observation.\n"
            "- Grid: 64x64, values 0-15 (colors). Actions: ACTION1-ACTION6.\n"
            "- Score increase = level completed. Same mechanics, new layout each level.\n"
            "- Every action costs a turn. Don't waste moves.\n"
            f"- Call `update_skill` to persist discoveries (game `{self.game_id}`). Knowledge dies without it."
        )

        # Spatial reasoning — compact
        spatial = getattr(self, '_spatial', None)
        if spatial and spatial.state == "enabled":
            size = spatial.player_size
            disp_str = ", ".join(
                f"{a}: ({dr},{dc})" for a, (dr, dc) in sorted(spatial.confirmed_displacements.items())
            )
            wall_str = str(set(spatial.confirmed_walls)) if spatial.confirmed_walls else "unknown"
            sections.append(
                f"## Spatial Model: player {size[0]}x{size[1]}, steps: {disp_str}, walls: {wall_str}"
            )
        sections.append(
            "## Navigation: locate yourself (Y,X), identify target, scan for walls, move toward target. "
            "If no_effect → you hit a wall, try a different direction."
        )

        # Load existing evolved skills for this game (per-level, from previous episodes)
        current_level = getattr(self, "current_level", 1)
        skill_base = Path(__file__).parent / "skills" / f"arc-{self.game_id}"

        # Load game-wide facts (always, never truncated)
        facts_path = skill_base / "FACTS.md"
        if facts_path.is_file():
            facts_content = facts_path.read_text(encoding="utf-8").strip()
            if facts_content:
                sections.append(
                    "## Universal Game Knowledge (CRITICAL — these facts apply to ALL levels)\n" + facts_content
                )

        # Load current level skill (agent's working copy)
        level_skill = skill_base / f"level{current_level}" / "SKILL.md"
        level_base = skill_base / f"level{current_level}" / "SKILL.base.md"
        skill_content = ""
        if level_skill.is_file():
            skill_content = level_skill.read_text(encoding="utf-8").strip()
        # Fall back to template if SKILL.md is missing or too short
        if len(skill_content) < 20 and level_base.is_file():
            skill_content = level_base.read_text(encoding="utf-8").strip()
        if skill_content:
            sections.append(
                f"## Your Evolved Skill — Level {current_level}\n{skill_content}"
            )

        # Legacy/previous level skills removed — FACTS.md provides game-wide knowledge

        return "\n\n".join(sections)

    def _messages_for_api(self, game_context: str = "") -> list[Any]:
        system = self._get_system_prompt().strip()
        # Merge history summary into system prompt (some providers reject multiple system messages)
        if self._history_summary:
            system += f"\n\n# HISTORY SUMMARY (earlier context)\n{self._history_summary}"
        parts: list[Any] = []
        if system:
            parts.append({"role": "system", "content": system})
        parts.extend(self.messages)
        return parts

    @property
    def name(self) -> str:
        obs = "with-observe" if self.DO_OBSERVATION else "no-observe"
        sanitized_model_name = self._model.replace("/", "-").replace(":", "-")
        return f"{super().name}.{sanitized_model_name}.{obs}"

    def is_done(self, frames: list[FrameData], latest_frame: FrameData) -> bool:
        return latest_frame.state is GameState.WIN

    def choose_action(self, frames: list[FrameData], latest_frame: FrameData) -> GameAction:
        logging.getLogger("openai").setLevel(logging.CRITICAL)
        logging.getLogger("httpx").setLevel(logging.CRITICAL)

        from arc.config import OPENROUTER_BASE_URL
        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY", "")
        client = OpenAIClient(api_key=api_key, base_url=OPENROUTER_BASE_URL)
        tools = self.build_tools()

        if len(self.messages) == 0:
            user_prompt = self.build_user_prompt(latest_frame)
            self.push_message({"role": "user", "content": user_prompt})
            self.push_message({
                "role": "assistant",
                "tool_calls": [{
                    "id": self._latest_tool_call_id,
                    "type": "function",
                    "function": {
                        "name": GameAction.RESET.name,
                        "arguments": json.dumps({}),
                    },
                }],
            })
            return GameAction.RESET

        function_response = self.build_func_resp_prompt(latest_frame)
        self.push_message({
            "role": "tool",
            "tool_call_id": self._latest_tool_call_id,
            "content": str(function_response),
        })

        if self.DO_OBSERVATION:
            logger.info("Sending to Assistant for observation...")
            try:
                create_kwargs: dict[str, Any] = {
                    "model": self._model,
                    "messages": self._messages_for_api(),
                }
                if self.REASONING_EFFORT is not None:
                    create_kwargs["reasoning_effort"] = self.REASONING_EFFORT
                if self._extra_body:
                    create_kwargs["extra_body"] = self._extra_body
                response = client.chat.completions.create(**create_kwargs)
            except openai.BadRequestError as e:
                logger.info(f"Message dump: {self.messages}")
                raise e
            obs_content = response.choices[0].message.content or ""
            self.track_tokens(response.usage.total_tokens, obs_content)
            self.push_message({"role": "assistant", "content": obs_content})
            logger.info(f"Assistant: {obs_content}")

        user_prompt = self.build_user_prompt(latest_frame)
        self.push_message({"role": "user", "content": user_prompt})

        name = GameAction.ACTION5.name
        arguments = None
        message5 = None

        logger.info("Sending to Assistant for action...")
        try:
            create_kwargs = {
                "model": self._model,
                "messages": self._messages_for_api(),
                "tools": tools,
                "tool_choice": "required",
            }
            if self.REASONING_EFFORT is not None:
                create_kwargs["reasoning_effort"] = self.REASONING_EFFORT
            if self._extra_body:
                create_kwargs["extra_body"] = self._extra_body
            response = client.chat.completions.create(**create_kwargs)
        except openai.BadRequestError as e:
            logger.info(f"Message dump: {self.messages}")
            raise e
        self.track_tokens(response.usage.total_tokens)
        message5 = response.choices[0].message

        if message5.tool_calls and len(message5.tool_calls) > 0:
            tool_call = message5.tool_calls[0]
            self._latest_tool_call_id = tool_call.id
            name = tool_call.function.name
            arguments = tool_call.function.arguments
            for tc in message5.tool_calls[1:]:
                self.push_message({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": "Error: only one action at a time.",
                })
        else:
            function_call = getattr(message5, "function_call", None)
            if function_call:
                name = function_call.name
                arguments = function_call.arguments or None

        if message5:
            self.push_message(message5)

        if arguments:
            try:
                data = json.loads(arguments) or {}
            except Exception:
                data = {}
        else:
            data = {}

        action = GameAction.from_name(name)
        action.set_data(data)
        return action

    def track_tokens(self, tokens: int, message: str = "") -> None:
        self.token_counter += tokens
        if hasattr(self, "_game_stats") and self._game_stats:
            self._game_stats.record_llm_call(
                self.game_id,
                getattr(self, "current_level", 1),
                tokens,
                step=len(getattr(self, "current_steps", [])),
            )
        if hasattr(self, "recorder"):
            self.recorder.record({
                "tokens": tokens,
                "total_tokens": self.token_counter,
                "assistant": message,
            })
        logger.info(f"Received {tokens} tokens, new total {self.token_counter}")

    def push_message(self, message: dict[str, Any]) -> list[dict[str, Any]]:
        self.messages.append(message)
        if len(self.messages) > self.MESSAGE_LIMIT:
            # Summarize the oldest messages before discarding
            n_to_remove = len(self.messages) - self.MESSAGE_LIMIT
            old_messages = self.messages[:n_to_remove]
            self._summarize_and_store(old_messages)
            self.messages = self.messages[n_to_remove:]
        # Ensure first message isn't an orphaned tool response
        while (
            len(self.messages) > 1
            and (
                self.messages[0].get("role")
                if isinstance(self.messages[0], dict)
                else getattr(self.messages[0], "role", None)
            ) == "tool"
        ):
            self.messages.pop(0)
        return self.messages

    def _summarize_and_store(self, old_messages: list[dict[str, Any]]) -> None:
        """Summarize old messages via LLM and append to rolling history summary."""
        # Extract text content from messages
        lines: list[str] = []
        for msg in old_messages:
            role = (
                msg.get("role", "?")
                if isinstance(msg, dict)
                else getattr(msg, "role", "?")
            )
            content = (
                msg.get("content", "")
                if isinstance(msg, dict)
                else getattr(msg, "content", "")
            )
            # Handle tool_calls in assistant messages
            tool_calls = (
                msg.get("tool_calls")
                if isinstance(msg, dict)
                else getattr(msg, "tool_calls", None)
            )
            if tool_calls:
                tc_names = []
                for tc in tool_calls:
                    if isinstance(tc, dict):
                        tc_names.append(tc.get("function", {}).get("name", "?"))
                    else:
                        tc_names.append(getattr(tc.function, "name", "?"))
                lines.append(f"[{role}] called: {', '.join(tc_names)}")
            elif content:
                # Truncate long content (grid dumps etc)
                text = str(content)
                if len(text) > 500:
                    text = text[:500] + "..."
                lines.append(f"[{role}] {text}")

        if not lines:
            return

        old_text = "\n".join(lines)

        # Use LLM to summarize
        try:
            from arc.config import OPENROUTER_BASE_URL
            api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY", "")
            client = OpenAIClient(api_key=api_key, base_url=OPENROUTER_BASE_URL)

            summary_prompt = (
                "Summarize the following game history into key findings. "
                "Focus on: action mappings discovered, score changes, "
                "what worked, what didn't, hypotheses formed. "
                "Be concise (max 200 words). Preserve specific coordinates and numbers.\n\n"
            )
            if self._history_summary:
                summary_prompt += f"PREVIOUS SUMMARY:\n{self._history_summary}\n\n"
            summary_prompt += f"NEW HISTORY TO INCORPORATE:\n{old_text}"

            create_kwargs = {
                "model": self._model,
                "messages": [{"role": "user", "content": summary_prompt}],
                "max_tokens": 400,
            }
            if self._extra_body:
                create_kwargs["extra_body"] = self._extra_body
            response = client.chat.completions.create(**create_kwargs)
            new_summary = response.choices[0].message.content or ""
            if new_summary:
                self._history_summary = new_summary.strip()
                logger.info("History summarized (%d chars)", len(self._history_summary))
        except Exception as e:
            # Fallback: simple text summary without LLM
            logger.warning("LLM summarization failed, using fallback: %s", e)
            fallback = old_text[-800:] if len(old_text) > 800 else old_text
            if self._history_summary:
                combined = self._history_summary + "\n" + fallback
                # Keep only the last 1200 chars
                self._history_summary = combined[-1200:]
            else:
                self._history_summary = fallback

    def build_functions(self) -> list[dict[str, Any]]:
        empty_params: dict[str, Any] = {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        }
        return [
            {"name": GameAction.RESET.name, "description": "Start or restart a game.", "parameters": empty_params},
            {"name": GameAction.ACTION1.name, "description": "Send input action (1, W, Up).", "parameters": empty_params},
            {"name": GameAction.ACTION2.name, "description": "Send input action (2, S, Down).", "parameters": empty_params},
            {"name": GameAction.ACTION3.name, "description": "Send input action (3, A, Left).", "parameters": empty_params},
            {"name": GameAction.ACTION4.name, "description": "Send input action (4, D, Right).", "parameters": empty_params},
            {"name": GameAction.ACTION5.name, "description": "Send input action (5, Enter, Spacebar).", "parameters": empty_params},
            {
                "name": GameAction.ACTION6.name,
                "description": "Send complex input action (6, Click, Point).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "string", "description": "Coordinate X, Int<0,63>"},
                        "y": {"type": "string", "description": "Coordinate Y, Int<0,63>"},
                    },
                    "required": ["x", "y"],
                    "additionalProperties": False,
                },
            },
        ]

    def build_tools(self) -> list[dict[str, Any]]:
        functions = self.build_functions()
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
            for f in functions
        ]

    def build_func_resp_prompt(self, latest_frame: FrameData) -> str:
        return textwrap.dedent(f"""\
# State:
{latest_frame.state.name}

# Score:
{getattr(latest_frame, 'score', latest_frame.levels_completed)}

# Frame:
{self.pretty_print_3d(latest_frame.frame)}

# TURN:
Reply with a few sentences of plain-text strategy observation.
        """)

    def build_user_prompt(self, latest_frame: FrameData) -> str:
        return textwrap.dedent("""\
# CONTEXT:
You are an agent playing a dynamic game. Your objective is to
WIN and avoid GAME_OVER while minimizing actions.

# TURN:
Call exactly one action.
        """)

    def pretty_print_3d(self, array_3d: list[list[list[Any]]]) -> str:
        lines = []
        for i, block in enumerate(array_3d):
            lines.append(f"Grid {i}:")
            for row in block:
                lines.append(f"  {row}")
            lines.append("")
        return "\n".join(lines)

    def cleanup(self, *args: Any, **kwargs: Any) -> None:
        if self._cleanup:
            if hasattr(self, "recorder"):
                meta = {
                    "llm_user_prompt": self.build_user_prompt(self.frames[-1]),
                    "llm_tools": self.build_tools() if self.MODEL_REQUIRES_TOOLS else self.build_functions(),
                    "llm_tool_resp_prompt": self.build_func_resp_prompt(self.frames[-1]),
                }
                self.recorder.record(meta)
        super().cleanup(*args, **kwargs)
