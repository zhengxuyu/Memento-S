"""LLM agent mixin for OpenAI-compatible tool-calling."""
import json
import logging
import os
import textwrap
from typing import Any, Optional

import openai
from arcengine import FrameData, GameAction, GameState
from openai import OpenAI as OpenAIClient

from arc.agent_base import Agent
from arc.skills_loader import format_skills_for_prompt, load_local_skills

logger = logging.getLogger()


class LLM(Agent):
    """An agent that uses a base LLM model to play games."""

    MAX_ACTIONS: int = 80
    DO_OBSERVATION: bool = True
    REASONING_EFFORT: Optional[str] = None
    MODEL_REQUIRES_TOOLS: bool = False
    MESSAGE_LIMIT: int = 10
    MODEL: str = "qwen/qwen3.5-397b-a17b"
    messages: list[dict[str, Any]]
    token_counter: int

    _latest_tool_call_id: str = "call_12345"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.messages = []
        self.token_counter = 0
        self._skills_system_prompt = None

    @property
    def _model(self) -> str:
        return os.environ.get("ARC_AGI_MODEL", "").strip() or self.MODEL

    @property
    def _extra_body(self) -> dict[str, Any] | None:
        provider = os.environ.get("OPENROUTER_PROVIDER", "").strip()
        if provider:
            return {"provider": {"order": [provider]}}
        return None

    def _get_system_prompt_with_skills(self, game_context: str = "") -> str:
        """Build system prompt with loaded skills."""
        if self._skills_system_prompt is not None:
            return self._skills_system_prompt
        try:
            skills = load_local_skills(max_content_chars=8000)
            self._skills_system_prompt = format_skills_for_prompt(
                skills,
                heading="You have the following skills available. Use them when relevant:",
            )
        except Exception as e:
            logger.warning("Could not load skills: %s", e)
            self._skills_system_prompt = ""
        return self._skills_system_prompt

    def _messages_for_api(self, game_context: str = "") -> list[Any]:
        system = self._get_system_prompt_with_skills(game_context).strip()
        if system:
            return [{"role": "system", "content": system}] + self.messages
        return self.messages

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
            self.messages = self.messages[-self.MESSAGE_LIMIT:]
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
