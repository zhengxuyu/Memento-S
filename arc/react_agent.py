"""ReactAgent: Minimal LLM-driven agent for ARC-AGI-3.

No built-in game strategies, no autopilot, no hypothesis engine.
The agent discovers everything through:
  1. Raw observation (grid state, score, action effects)
  2. LLM reasoning (observe → think → act)
  3. Episode memory (few-shot from past episodes)
"""
from __future__ import annotations

import ast
import io
import json
import logging
import os
import signal
import threading
import time
from pathlib import Path
from typing import Any, Optional

import openai
from arcengine import FrameData, GameAction, GameState
from openai import OpenAI as OpenAIClient

from arc.config import (
    MAX_ACTIONS,
    MAX_RETRIES,
    API_RETRIES,
    MEMORY_DIR,
    MEMORY_WARMUP,
)
from arc.llm_agent import LLM
from arc.prompts import build_func_resp_prompt, build_user_prompt

logger = logging.getLogger(__name__)

# Hard timeout for API calls (signal.alarm based).
# httpx read timeout doesn't cover chunked body stalls from OpenRouter.
_HARD_TIMEOUT = 60  # seconds


class _HardTimeout:
    """Context manager: raises TimeoutError after _HARD_TIMEOUT seconds via SIGALRM."""

    def __enter__(self):
        self._old = signal.signal(signal.SIGALRM, self._handler)
        signal.alarm(_HARD_TIMEOUT)
        return self

    def __exit__(self, *exc):
        signal.alarm(0)
        signal.signal(signal.SIGALRM, self._old)
        return False

    @staticmethod
    def _handler(signum, frame):
        raise TimeoutError(f"API call exceeded {_HARD_TIMEOUT}s hard timeout")


_GAME_ACTIONS = frozenset({
    GameAction.ACTION1.name, GameAction.ACTION2.name,
    GameAction.ACTION3.name, GameAction.ACTION4.name,
    GameAction.ACTION5.name, GameAction.ACTION6.name,
    GameAction.RESET.name,
})

_TOOL_HANDLERS = {
    "update_skill": "_handle_update_skill",
    "load_skill": "_handle_load_skill",
    # "run_code": "_handle_run_code",  # disabled to reduce token waste
}


class EpisodeMemory:
    """Persistent episode memory with embedding-based retrieval.

    Episodes are stored per game on disk (JSONL + numpy embeddings).
    Retrieval uses OpenRouter embeddings + FAISS for similarity search.
    Falls back to longest-common-prefix if embedding fails.
    """

    EMBED_MODEL = "openai/text-embedding-3-small"

    def __init__(self, game_id: str, memory_dir: str = MEMORY_DIR, warmup: int = MEMORY_WARMUP) -> None:
        self.game_id = game_id
        self.warmup = warmup
        self._dir = Path(memory_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._file = self._dir / f"{game_id}.jsonl"
        self._emb_file = self._dir / f"{game_id}_emb.npy"
        self.episodes: list[dict[str, Any]] = []
        self._embeddings: Optional[Any] = None  # numpy array (N, dim)
        self._faiss_index: Optional[Any] = None
        self._load()

    def _load(self) -> None:
        """Load episodes and embeddings from disk."""
        if not self._file.exists():
            return
        try:
            for line in self._file.read_text(encoding="utf-8").strip().splitlines():
                if line.strip():
                    self.episodes.append(json.loads(line))
            logger.info("Episode memory: loaded %d episodes for %s", len(self.episodes), self.game_id)
        except Exception as e:
            logger.warning("Episode memory: failed to load %s: %s", self._file, e)
            return

        # Load embeddings
        if self._emb_file.exists() and self.episodes:
            try:
                import numpy as np
                self._embeddings = np.load(self._emb_file)
                if len(self._embeddings) == len(self.episodes):
                    self._build_faiss_index()
                else:
                    logger.warning("Episode memory: embedding count mismatch, will re-embed")
                    self._embeddings = None
            except Exception as e:
                logger.warning("Episode memory: failed to load embeddings: %s", e)

    def _append_to_disk(self, episode: dict[str, Any]) -> None:
        """Append one episode to the JSONL file."""
        try:
            with open(self._file, "a", encoding="utf-8") as f:
                json.dump(episode, f, ensure_ascii=False)
                f.write("\n")
        except Exception as e:
            logger.warning("Episode memory: failed to save: %s", e)

    def _save_embeddings(self) -> None:
        """Save all embeddings to disk."""
        if self._embeddings is not None:
            try:
                import numpy as np
                np.save(self._emb_file, self._embeddings)
            except Exception as e:
                logger.warning("Episode memory: failed to save embeddings: %s", e)

    def _episode_to_text(self, ep: dict[str, Any]) -> str:
        """Convert an episode to a text string for embedding."""
        parts = [f"score:{ep['score']} result:{ep['result']}"]
        for act, eff in zip(ep["actions"], ep["effects"]):
            parts.append(f"{act}->{eff}")
        return " | ".join(parts)

    def _get_embedding(self, texts: list[str]) -> Optional[Any]:
        """Get embeddings via OpenRouter API."""
        try:
            import numpy as np
            from arc.config import OPENROUTER_BASE_URL
            api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY", "")
            client = OpenAIClient(api_key=api_key, base_url=OPENROUTER_BASE_URL)

            response = client.embeddings.create(
                model=self.EMBED_MODEL,
                input=texts,
            )
            vecs = [item.embedding for item in response.data]
            return np.array(vecs, dtype="float32")
        except Exception as e:
            logger.warning("Episode memory: embedding failed: %s", e)
            return None

    def _build_faiss_index(self) -> None:
        """Build FAISS index from current embeddings."""
        if self._embeddings is None or len(self._embeddings) == 0:
            return
        try:
            import faiss
            dim = self._embeddings.shape[1]
            self._faiss_index = faiss.IndexFlatIP(dim)  # inner product (cosine after normalize)
            import numpy as np
            # L2-normalize for cosine similarity
            norms = np.linalg.norm(self._embeddings, axis=1, keepdims=True)
            norms[norms == 0] = 1
            normalized = self._embeddings / norms
            self._faiss_index.add(normalized)
        except ImportError:
            logger.info("Episode memory: faiss not available, using brute-force fallback")
            self._faiss_index = None
        except Exception as e:
            logger.warning("Episode memory: faiss index build failed: %s", e)
            self._faiss_index = None

    def record(self, steps: list[dict], score: int, result: str) -> None:
        """Store a completed episode (memory + disk + embedding)."""
        ep = {
            "actions": [s.get("action", "?") for s in steps],
            "effects": [s.get("effect", "?") for s in steps],
            "score": score,
            "result": result,
        }
        self.episodes.append(ep)
        self._append_to_disk(ep)

        # Compute and store embedding
        text = self._episode_to_text(ep)
        emb = self._get_embedding([text])
        if emb is not None:
            import numpy as np
            if self._embeddings is None:
                self._embeddings = emb
            else:
                self._embeddings = np.vstack([self._embeddings, emb])
            self._save_embeddings()
            self._build_faiss_index()

        logger.info(
            "Episode memory: stored ep #%d (%d actions, score=%d, %s)",
            len(self.episodes), len(steps), score, result,
        )

    def retrieve(self, current_actions: list[str], current_effects: list[str], k: int = 3) -> list[dict[str, Any]]:
        """Find k most similar past episodes using embeddings + FAISS."""
        if not self.episodes:
            return []

        k = min(k, len(self.episodes))

        # Try embedding-based retrieval
        if self._embeddings is not None and len(self._embeddings) == len(self.episodes):
            query_parts = []
            for act, eff in zip(current_actions, current_effects):
                query_parts.append(f"{act}->{eff}")
            query_text = " | ".join(query_parts) if query_parts else "start"
            query_emb = self._get_embedding([query_text])

            if query_emb is not None:
                import numpy as np
                # Normalize query
                norm = np.linalg.norm(query_emb)
                if norm > 0:
                    query_emb = query_emb / norm

                if self._faiss_index is not None:
                    distances, indices = self._faiss_index.search(query_emb, k)
                    return [self.episodes[idx] for idx in indices[0] if 0 <= idx < len(self.episodes)]
                else:
                    # Brute-force cosine similarity
                    norms = np.linalg.norm(self._embeddings, axis=1, keepdims=True)
                    norms[norms == 0] = 1
                    normed = self._embeddings / norms
                    scores = (normed @ query_emb.T).flatten()
                    top_indices = np.argsort(scores)[-k:][::-1]
                    return [self.episodes[idx] for idx in top_indices]

        # Fallback: longest common prefix
        return self._retrieve_by_prefix(current_actions, k)

    def _retrieve_by_prefix(self, current_actions: list[str], k: int) -> list[dict[str, Any]]:
        """Fallback retrieval by longest common action prefix."""
        scored: list[tuple[float, int]] = []
        for idx, ep in enumerate(self.episodes):
            past_actions = ep["actions"]
            lcp = 0
            for a, b in zip(current_actions, past_actions):
                if a == b:
                    lcp += 1
                else:
                    break
            similarity = lcp + ep["score"] * 0.01
            scored.append((similarity, idx))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [self.episodes[idx] for _, idx in scored[:k]]

    def build_few_shot(self, current_actions: list[str], current_effects: list[str]) -> str:
        """Build few-shot context from similar past episodes.

        Returns empty string if still in warmup phase.
        """
        if len(self.episodes) < self.warmup:
            return ""

        similar = self.retrieve(current_actions, current_effects, k=3)
        if not similar:
            return ""

        lines = ["# PAST EPISODE EXAMPLES (most similar to current attempt)"]
        for i, ep in enumerate(similar, 1):
            actions = ep["actions"]
            effects = ep["effects"]
            score = ep["score"]
            result = ep["result"]

            lines.append(f"\n## Episode {i} — final score: {score}, result: {result}")
            lines.append("Actions:")
            for step_idx, (act, eff) in enumerate(zip(actions, effects), 1):
                lines.append(f"  {step_idx}. {act} -> {eff}")

        return "\n".join(lines)


class ReactAgent(LLM):
    """Minimal ReAct agent — LLM + raw game state, no programmatic help."""

    def __init__(self, *args: Any, memory: bool = True, memory_warmup: int = MEMORY_WARMUP,
                 arcade: Any = None, shortcut: bool = False, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        # Episode state
        self.current_steps: list[dict] = []
        self.retry_count: int = 0
        self._last_score: int = 0
        self.current_level: int = 1  # Current level (1-indexed, = score + 1)
        self._arcade = arcade  # For scorecard submission

        # Shortcut mode: replay solved levels without LLM
        self._shortcut_enabled = shortcut
        self._shortcut_file = Path(MEMORY_DIR) / f"{self.game_id}_shortcuts.json"
        self._shortcuts: dict[str, list[str]] = self._load_shortcuts()

        # Episode memory for few-shot learning (per-level)
        self._memory_enabled = memory
        self._memory_warmup = memory_warmup
        self.episode_memory = EpisodeMemory(
            game_id=f"{self.game_id}_level{self.current_level}",
            warmup=memory_warmup,
        ) if memory else None


    # ------------------------------------------------------------------
    # Main loop — retry on failure
    # ------------------------------------------------------------------

    STOP_FILE = Path("/tmp/arc_stop")

    def _submit_scorecard(self) -> None:
        """Submit scorecard to arcade (idempotent, safe to call multiple times)."""
        if not self._arcade:
            return
        try:
            result = self._arcade.close_scorecard()
            if result:
                logger.info("Scorecard submitted: score=%.1f", result.score)
        except Exception as e:
            logger.warning("Scorecard submission failed: %s", e)

    def _check_stop(self) -> bool:
        """Check if external stop signal file exists and contains 'True'."""
        try:
            if self.STOP_FILE.is_file():
                content = self.STOP_FILE.read_text().strip().lower()
                if content in ("true", "1", "stop"):
                    return True
        except Exception:
            pass
        return False

    def _clear_stop(self) -> None:
        """Clear the stop file on startup."""
        try:
            if self.STOP_FILE.exists():
                self.STOP_FILE.unlink()
        except Exception:
            pass

    def _load_shortcuts(self) -> dict[str, list[str]]:
        """Load saved winning paths per level."""
        try:
            if self._shortcut_file.is_file():
                data = json.loads(self._shortcut_file.read_text(encoding="utf-8"))
                logger.info("Shortcuts loaded: %d levels solved", len(data))
                return data
        except Exception as e:
            logger.warning("Failed to load shortcuts: %s", e)
        return {}

    def _save_shortcut(self, level: int, actions: list[str]) -> None:
        """Save the winning action sequence for a level (only if shorter)."""
        existing = self._shortcuts.get(str(level))
        if existing and len(existing) <= len(actions):
            logger.info("Shortcut not updated: level %d existing (%d) <= new (%d)",
                        level, len(existing), len(actions))
            return
        self._shortcuts[str(level)] = actions
        try:
            self._shortcut_file.parent.mkdir(parents=True, exist_ok=True)
            self._shortcut_file.write_text(
                json.dumps(self._shortcuts, indent=2), encoding="utf-8",
            )
            logger.info("Shortcut saved: level %d → %d actions", level, len(actions))
        except Exception as e:
            logger.warning("Failed to save shortcut: %s", e)

    def _replay_shortcut(self, level: int) -> bool:
        """Replay a saved winning path. Returns True if level_up achieved."""
        actions = self._shortcuts.get(str(level))
        if not actions:
            return False
        logger.info("SHORTCUT: replaying %d actions for level %d", len(actions), level)
        for i, action_name in enumerate(actions):
            frame = self.frames[-1]
            if frame.state is GameState.WIN:
                return True
            if frame.state is GameState.GAME_OVER:
                logger.warning("SHORTCUT: game_over during replay at step %d", i)
                return False
            self._execute_action(action_name, "{}")
            # Check if score increased
            curr_score = self._frame_score(self.frames[-1])
            if curr_score > level - 1:  # level N expects score to go from N-1 to N
                logger.info("SHORTCUT: level %d completed at step %d/%d", level, i + 1, len(actions))
                return True
        logger.warning("SHORTCUT: replayed all %d actions but level %d not completed", len(actions), level)
        return False

    def _archive_skill(self, episode_result: str) -> None:
        """Copy current skill files to timestamped archive after each episode."""
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        skill_base = Path(__file__).parent / "skills" / f"arc-{self.game_id}"

        # Archive per-level skills that exist
        for level_dir in sorted(skill_base.glob("level*")):
            for skill_file in level_dir.glob("SKILL.md"):
                content = skill_file.read_text(encoding="utf-8").strip()
                if len(content) < 10:
                    continue  # skip empty/trivial files
                archive_name = f"SKILL.{episode_result}.r{self.retry_count}.{ts}.md"
                archive_path = level_dir / archive_name
                archive_path.write_text(content, encoding="utf-8")
                logger.info("Archived %s → %s", skill_file.name, archive_path.name)

        # Archive legacy SKILL.md if it exists
        legacy = skill_base / "SKILL.md"
        if legacy.is_file():
            content = legacy.read_text(encoding="utf-8").strip()
            if len(content) >= 10:
                archive_name = f"SKILL.{episode_result}.r{self.retry_count}.{ts}.md"
                archive_path = skill_base / archive_name
                archive_path.write_text(content, encoding="utf-8")
                logger.info("Archived legacy SKILL.md → %s", archive_path.name)

    def main(self) -> None:
        self.timer = time.time()
        self._clear_stop()
        logger.info("Stop file: write 'True' to %s to gracefully stop", self.STOP_FILE)

        while True:
            result = self._play_episode()

            # Archive skill file after each episode
            self._archive_skill(result)

            if result == "win":
                if self.episode_memory:
                    self.episode_memory.record(self.current_steps, self._last_score, "win")
                logger.info(
                    "WIN on attempt %d! Total actions: %d, time: %.1fs",
                    self.retry_count + 1, self.action_counter, self.seconds,
                )
                break
            elif result in ("game_over", "max_actions"):
                if self.episode_memory:
                    self.episode_memory.record(self.current_steps, self._last_score, result)
                self.retry_count += 1
                if self.retry_count >= MAX_RETRIES:
                    logger.info("Max retries (%d) exhausted, stopping", MAX_RETRIES)
                    break
                logger.info(
                    "%s — retrying level %d (attempt #%d), score=%d, actions=%d",
                    result.upper(), self.current_level, self.retry_count + 1,
                    self._last_score, self.action_counter,
                )
                self._reset_for_retry()
            elif result == "stopped":
                if self.episode_memory:
                    self.episode_memory.record(self.current_steps, self._last_score, "stopped")
                logger.info("Gracefully stopped at level %d, score=%d", self.current_level, self._last_score)
                break
            else:
                logger.info("Episode ended: %s", result)
                break

        self._generate_live_video()
        self.cleanup()
        self._submit_scorecard()

    # ------------------------------------------------------------------
    # Play one episode
    # ------------------------------------------------------------------

    def _play_episode(self) -> str:
        """Play one episode (one level attempt).

        Returns 'win', 'game_over', 'max_actions', or 'level_up'.
        """
        # RESET initializes the game and gets the first grid — required
        frame = self.take_action(GameAction.RESET)
        if frame:
            self.append_frame(frame)
        self.last_action_name = "RESET"
        self._last_score = self._frame_score(self.frames[-1])
        score_at_episode_start = self._last_score

        # Shortcut: replay all solved levels without LLM
        if self._shortcut_enabled:
            while str(self.current_level) in self._shortcuts:
                if self._replay_shortcut(self.current_level):
                    # Level completed via shortcut
                    completed_level = self.current_level
                    self._last_score = self._frame_score(self.frames[-1])
                    self._force_level_up_summary(completed_level)
                    self.current_level = self._last_score + 1
                    score_at_episode_start = self._last_score
                    self.current_steps = []
                    logger.info("SHORTCUT: fast-forwarded to level %d (score=%d)",
                                self.current_level, self._last_score)
                    self._generate_live_video()
                    latest = self.frames[-1]
                    if latest.state is GameState.WIN:
                        return "win"
                else:
                    # Shortcut failed — fall through to LLM
                    logger.warning("SHORTCUT: replay failed for level %d, falling back to LLM",
                                   self.current_level)
                    break

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
        consecutive_tool_calls = 0
        consecutive_nones = 0
        MAX_CONSECUTIVE_TOOLS = 3
        MAX_CONSECUTIVE_NONES = 5
        skip_obs = False  # True after tool calls — go straight to LLM, no env call
        while True:
            if not skip_obs:
                latest = self.frames[-1]

                # Check terminal states
                if latest.state is GameState.WIN:
                    return "win"
                if latest.state is GameState.GAME_OVER:
                    return "game_over"

                # Check score BEFORE max_actions — if the last action scored,
                # we must save the shortcut before returning "max_actions"
                curr_score = self._frame_score(latest)
                if curr_score > score_at_episode_start:
                    self._last_score = curr_score
                    completed_level = self.current_level
                    # Save winning path for shortcut replay
                    winning_actions = [s["action"] for s in self.current_steps]
                    self._save_shortcut(completed_level, winning_actions)
                    # Record memory for completed level
                    if self.episode_memory:
                        self.episode_memory.record(self.current_steps, self._last_score, "level_up")
                    # Bootstrap new level skill from completed level's skill
                    self._force_level_up_summary(completed_level)
                    self.current_level = self._last_score + 1
                    logger.info(
                        "LEVEL UP to level %d! actions=%d, retries_used=%d",
                        self.current_level, self.action_counter, self.retry_count,
                    )
                    # Switch to new per-level episode memory
                    if self._memory_enabled:
                        self.episode_memory = EpisodeMemory(
                            game_id=f"{self.game_id}_level{self.current_level}",
                            warmup=self._memory_warmup,
                        )
                    self.current_steps = []
                    self.retry_count = 0
                    step_count = 0
                    score_at_episode_start = curr_score
                    # Continue playing — no RESET, no return

                # Check external stop signal
                if self._check_stop():
                    logger.info("External stop signal detected, stopping gracefully")
                    return "stopped"

                # Build observation and call LLM
                obs = self._build_observation(latest)
                action_result = self._llm_step(obs)
            else:
                # Tool result already in messages — call LLM without new observation
                skip_obs = False
                action_result = self._llm_step("")

            if action_result:
                consecutive_nones = 0
                tc_name, tc_args, tc_id, reasoning = action_result
                self._latest_tool_call_id = tc_id
                # Route action
                if tc_name in _GAME_ACTIONS:
                    self._execute_action(tc_name, tc_args, reasoning=reasoning)
                    step_count += 1
                    consecutive_tool_calls = 0
                    # Force update_skill every 5 actions (independent LLM call)
                    if step_count % 5 == 0:
                        self._force_skill_update()
                    skip_obs = False  # let main loop build observation normally
                    if step_count % 5 == 0:
                        self._generate_live_video()
                elif tc_name in _TOOL_HANDLERS:
                    consecutive_tool_calls += 1
                    if consecutive_tool_calls > MAX_CONSECUTIVE_TOOLS:
                        logger.warning("Too many consecutive tool calls (%d), forcing observation rebuild", consecutive_tool_calls)
                        self.push_message({
                            "role": "tool",
                            "tool_call_id": tc_id,
                            "content": "STOP using tools. You MUST call a game action (ACTION1-ACTION6) NOW.",
                        })
                        consecutive_tool_calls = 0
                        skip_obs = False  # Force rebuild observation to break the loop
                    else:
                        handler = getattr(self, _TOOL_HANDLERS[tc_name])
                        result = handler(tc_args)
                        self.push_message({
                            "role": "tool",
                            "tool_call_id": tc_id,
                            "content": result,
                        })
                        skip_obs = True  # Don't call env, go straight to LLM
                else:
                    logger.warning("Invalid action: %s", tc_name)
                    self.push_message({
                        "role": "tool",
                        "tool_call_id": tc_id,
                        "content": f"Error: '{tc_name}' is not a valid action. Use ACTION1-ACTION6, update_skill, or load_skill.",
                    })
                    skip_obs = True  # Don't call env, let LLM retry
            else:
                # LLM returned None (no action)
                consecutive_nones += 1
                if consecutive_nones >= MAX_CONSECUTIVE_NONES:
                    logger.warning("LLM returned None %d times in a row — resending observation", consecutive_nones)
                    consecutive_nones = 0
                    skip_obs = False  # Force rebuild observation to unstick
                else:
                    skip_obs = True

    # ------------------------------------------------------------------
    # Observation
    # ------------------------------------------------------------------

    def _build_observation(self, latest: FrameData) -> str:
        """Build observation prompt — raw game state + few-shot + situation skills."""
        action_history = self._build_action_history()

        # Few-shot from episode memory (after warmup phase)
        few_shot = ""
        if self.episode_memory:
            current_actions = [s.get("action", "?") for s in self.current_steps]
            current_effects = [s.get("effect", "?") for s in self.current_steps]
            few_shot = self.episode_memory.build_few_shot(current_actions, current_effects)

        # Situation-based thinking tools (injected per step)
        from arc.skill_selector import select_skills
        thinking_tools = select_skills(
            current_steps=self.current_steps,
            retry_count=self.retry_count,
            max_actions=MAX_ACTIONS,
        )

        function_catalog = ""  # run_code disabled

        return build_func_resp_prompt(
            latest_frame=latest,
            frames=self.frames,
            last_action_name=getattr(self, "last_action_name", ""),
            retry_count=self.retry_count,
            current_steps=self.current_steps,
            max_retries=MAX_RETRIES,
            action_history=action_history,
            few_shot=few_shot,
            thinking_tools=thinking_tools,
            function_catalog=function_catalog,
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

    def _get_function_catalog(self) -> str:
        """Return a catalog of saved functions for prompt injection."""
        func_dir = Path(__file__).parent / "skills" / f"arc-{self.game_id}" / "functions"
        if not func_dir.is_dir():
            return ""
        entries = []
        for py_file in sorted(func_dir.glob("*.py")):
            fname = py_file.stem
            try:
                content = py_file.read_text(encoding="utf-8")
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        args = ", ".join(a.arg for a in node.args.args)
                        doc = ast.get_docstring(node) or fname
                        entries.append(f"- `{fname}({args})`: {doc}")
                        break
                else:
                    entries.append(f"- `{fname}()`: (no signature found)")
            except Exception:
                entries.append(f"- `{fname}()`: (parse error)")
        if not entries:
            return ""
        return "# Available Functions (pre-loaded in run_code)\n" + "\n".join(entries)

    # ------------------------------------------------------------------
    # LLM call
    # ------------------------------------------------------------------

    # Valid action names for parsing from reasoning text
    _ACTION_NAMES = frozenset({
        "ACTION1", "ACTION2", "ACTION3", "ACTION4", "ACTION5", "ACTION6", "RESET",
    })

    @staticmethod
    def _is_funds_error(exc: Exception) -> bool:
        """Check if an API error is due to insufficient funds/credits."""
        msg = str(exc).lower()
        if any(kw in msg for kw in ("insufficient", "funds", "credits", "payment", "billing", "quota")):
            return True
        if hasattr(exc, "status_code") and exc.status_code == 402:
            return True
        return False

    def _create_completion(self, client: Any, **kwargs: Any) -> Any:
        """Wrapper: chat.completions.create with infinite retry on insufficient funds."""
        while True:
            try:
                with _HardTimeout():
                    return client.chat.completions.create(**kwargs)
            except Exception as e:
                if self._is_funds_error(e):
                    logger.warning("Insufficient funds — waiting 60s before retry: %s", e)
                    time.sleep(60)
                    continue
                raise

    def _parse_action_from_text(self, text: str) -> Optional[str]:
        """Try to extract an action name from reasoning text.

        Handles formats like: "ACTION1", "ACTION1{}", "I'll try ACTION3", etc.
        """
        import re
        # Look for ACTION[1-6] or RESET in the text
        m = re.search(r'\b(ACTION[1-6]|RESET)\b', text)
        if m:
            return m.group(1)
        return None

    def _llm_step(self, observation: str) -> Optional[tuple[str, str, str, str]]:
        """Single LLM call: observation → reasoning + action.

        Strategy:
        1. Call with tool_choice="auto" to get reasoning + possibly tool call
        2. If tool call returned, use it directly
        3. If only reasoning, parse action name from text (fast, no API call)
        4. If parsing fails, fall back to Phase 2 with tool_choice="required"

        Returns (tool_name, tool_args_json, tool_call_id, reasoning) or None.
        """
        # Push observation as tool response
        if observation:
            self.push_message({
                "role": "tool",
                "tool_call_id": self._latest_tool_call_id,
                "content": observation,
            })

        from arc.config import OPENROUTER_BASE_URL, API_TIMEOUT
        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY", "")
        client = OpenAIClient(
            api_key=api_key,
            base_url=OPENROUTER_BASE_URL,
            timeout=API_TIMEOUT,
        )

        tools = self._build_tools()

        # Phase 1: Get reasoning + possibly tool call
        reasoning = ""
        for attempt in range(API_RETRIES):
            try:
                create_kwargs: dict[str, Any] = {
                    "model": self._model,
                    "messages": self._messages_for_api(),
                    "tools": tools,
                    "tool_choice": "auto",
                }
                extra = self._extra_body
                if extra:
                    create_kwargs["extra_body"] = extra

                response = self._create_completion(client, **create_kwargs)
                break
            except openai.BadRequestError:
                logger.warning("BadRequestError on attempt %d", attempt + 1)
                if attempt == API_RETRIES - 1:
                    return None
            except (openai.APIConnectionError, openai.RateLimitError,
                    openai.APITimeoutError, TimeoutError) as e:
                logger.warning("API error on attempt %d: %s", attempt + 1, e)
                if attempt == API_RETRIES - 1:
                    return None
                time.sleep(2 ** attempt)
        else:
            return None

        self.track_tokens(response.usage.total_tokens if response.usage else 0)
        if not response.choices:
            logger.warning("Empty choices from API")
            return None
        message = response.choices[0].message

        reasoning = message.content or ""
        # OpenRouter returns thinking/reasoning in a separate field
        reasoning_content = getattr(message, "reasoning_content", None) or getattr(message, "reasoning", None) or ""
        if reasoning_content and not reasoning:
            reasoning = reasoning_content
        elif reasoning_content and reasoning:
            reasoning = f"[Thinking] {reasoning_content}\n\n{reasoning}"
        if reasoning:
            logger.info("LLM reasoning: %s", reasoning[:300])

        # If model returned tool calls, use them directly
        if message.tool_calls:
            return self._process_tool_calls(message, reasoning)

        # No tool call — try to parse action from reasoning text (fast path)
        if reasoning:
            parsed_action = self._parse_action_from_text(reasoning)
            if parsed_action:
                tc_id = f"parsed_{self.action_counter}_{int(time.time())}"
                logger.info("Parsed action from reasoning: %s", parsed_action)
                # Inject as assistant message with synthetic tool call
                self.push_message({
                    "role": "assistant",
                    "content": reasoning,
                    "tool_calls": [{
                        "id": tc_id,
                        "type": "function",
                        "function": {"name": parsed_action, "arguments": "{}"},
                    }],
                })
                return (parsed_action, "{}", tc_id, reasoning)

            # Phase 2 fallback: no action parseable, force tool call
            self.push_message({"role": "assistant", "content": reasoning})
            self.push_message({"role": "user", "content": "Now call exactly one action tool."})

            for attempt in range(API_RETRIES):
                try:
                    create_kwargs = {
                        "model": self._model,
                        "messages": self._messages_for_api(),
                        "tools": tools,
                        "tool_choice": "required",
                    }
                    extra = self._extra_body
                    if extra:
                        create_kwargs["extra_body"] = extra
                    response = self._create_completion(client, **create_kwargs)
                    break
                except (openai.BadRequestError, openai.APIConnectionError,
                        openai.RateLimitError, openai.APITimeoutError,
                        TimeoutError) as e:
                    logger.warning("Phase 2 API error on attempt %d: %s", attempt + 1, e)
                    if attempt == API_RETRIES - 1:
                        return None
                    time.sleep(2 ** attempt)
            else:
                return None

            self.track_tokens(response.usage.total_tokens if response.usage else 0)
            if not response.choices:
                logger.warning("Empty choices from Phase 2 API")
                return None
            message = response.choices[0].message

            if message.tool_calls:
                return self._process_tool_calls(message, reasoning)

        return None

    def _process_tool_calls(self, message: Any, reasoning: str) -> Optional[tuple[str, str, str, str]]:
        """Process tool calls from LLM response."""
        if message.tool_calls:
            tc = message.tool_calls[0]
            self.push_message(message)
            return (
                tc.function.name,
                tc.function.arguments or "{}",
                tc.id,
                reasoning,
            )
        return None

    def _build_tools(self) -> list[dict[str, Any]]:
        """Build tool list: ACTION1-6 + update_skill + load_skill + run_code."""
        tools = self.build_tools()
        tools.append({
            "type": "function",
            "function": {
                "name": "update_skill",
                "description": (
                    "Write/update the skill file to persist your discoveries about this game. "
                    "Call this whenever you learn something new (action mappings, scoring rules, "
                    "grid patterns, strategies). Content should be complete — it REPLACES the file."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "Full SKILL.md content (YAML frontmatter + markdown body)",
                        },
                    },
                    "required": ["content"],
                },
            },
        })
        tools.append({
            "type": "function",
            "function": {
                "name": "load_skill",
                "description": (
                    "Read a thinking tool's full SKILL.md procedure. "
                    "The observation prompt shows short summaries — use this to get the complete content. "
                    "Pass name='list' to see all available skills."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Skill directory name (e.g. 'jootsing'), prefix, or 'list' for all",
                        },
                    },
                    "required": ["name"],
                },
            },
        })
        # run_code disabled to reduce token waste
        return tools

    def _force_skill_update(self) -> None:
        """Force LLM to call update_skill after a game action.

        Uses an independent message list (not the main conversation) to avoid
        Gemini's strict tool_call/tool_response pairing errors.
        """
        latest = self.frames[-1]
        obs = self._build_observation(latest)

        # Load current skill + template for context
        skill_base = Path(__file__).parent / "skills" / f"arc-{self.game_id}" / f"level{self.current_level}"
        skill_content = ""
        skill_path = skill_base / "SKILL.md"
        if skill_path.is_file():
            try:
                skill_content = skill_path.read_text(encoding="utf-8")
            except Exception:
                pass
        base_content = ""
        base_path = skill_base / "SKILL.base.md"
        if base_path.is_file():
            try:
                base_content = base_path.read_text(encoding="utf-8")
            except Exception:
                pass
        # Use template as fallback if working copy is empty/junk
        if len(skill_content.strip()) < 20 and base_content:
            skill_content = base_content

        # Build a standalone message list — no shared conversation history
        messages = [
            {"role": "system", "content": (
                "You are updating a skill file for an ARC-AGI-3 grid game. "
                "Based on the observation below, call update_skill with the FULL updated SKILL.md content. "
                "Preserve all existing knowledge and add new discoveries."
            )},
            {"role": "user", "content": (
                f"# Current Skill File:\n```\n{skill_content}\n```\n\n"
                f"# Latest Observation:\n{obs}\n\n"
                "Call update_skill with the updated SKILL.md content now."
            )},
        ]

        from arc.config import OPENROUTER_BASE_URL, API_TIMEOUT
        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY", "")
        client = OpenAIClient(
            api_key=api_key,
            base_url=OPENROUTER_BASE_URL,
            timeout=API_TIMEOUT,
        )

        # Only offer update_skill tool, force its selection
        update_tool = [t for t in self._build_tools() if t["function"]["name"] == "update_skill"]

        for attempt in range(API_RETRIES):
            try:
                create_kwargs: dict[str, Any] = {
                    "model": self._model,
                    "messages": messages,
                    "tools": update_tool,
                    "tool_choice": {"type": "function", "function": {"name": "update_skill"}},
                }
                extra = self._extra_body
                if extra:
                    create_kwargs["extra_body"] = extra
                response = self._create_completion(client, **create_kwargs)
                break
            except (openai.BadRequestError, openai.APIConnectionError,
                    openai.RateLimitError, openai.APITimeoutError,
                    TimeoutError) as e:
                logger.warning("Force update_skill API error on attempt %d: %s", attempt + 1, e)
                if attempt == API_RETRIES - 1:
                    return
                time.sleep(2 ** attempt)
        else:
            return

        self.track_tokens(response.usage.total_tokens if response.usage else 0)
        if not response.choices:
            return

        message = response.choices[0].message
        if message.tool_calls:
            tc = message.tool_calls[0]
            result = self._handle_update_skill(tc.function.arguments or "{}")
            logger.info("Forced skill update completed")
        else:
            logger.warning("Force update_skill: LLM did not return tool call")

    def _force_level_up_summary(self, completed_level: int) -> None:
        """After level-up, force LLM to bootstrap the new level's skill from the old one.

        Reads the completed level's skill, asks LLM to extract key takeaways,
        and writes the result as the starting skill for the new level.
        """
        new_level = completed_level + 1
        skill_base = Path(__file__).parent / "skills" / f"arc-{self.game_id}"

        # Load completed level's skill
        prev_skill = skill_base / f"level{completed_level}" / "SKILL.md"
        if not prev_skill.is_file():
            # Try legacy path
            prev_skill = skill_base / "SKILL.md"
        if not prev_skill.is_file():
            logger.info("No previous skill to summarize for level %d", completed_level)
            return
        prev_content = prev_skill.read_text(encoding="utf-8").strip()
        if not prev_content:
            return

        # Build standalone LLM call
        messages = [
            {"role": "system", "content": (
                "You are distilling a CHEAT SHEET for the next level of an ARC-AGI-3 grid game. "
                "The next level has the SAME mechanics but a DIFFERENT layout.\n\n"
                "Write a CONCISE, ACTIONABLE skill file. Use this EXACT structure:\n\n"
                "```\n"
                "---\n"
                "name: \"<short name>\"\n"
                "description: \"<one line>\"\n"
                "---\n"
                "# How To Win (step-by-step)\n"
                "1. <first thing to do>\n"
                "2. <second thing to do>\n"
                "...\n\n"
                "# Controls\n"
                "- Action 1: <what it does>\n"
                "...\n\n"
                "# Key Facts\n"
                "- <critical fact 1>\n"
                "- <critical fact 2>\n"
                "...\n"
                "```\n\n"
                "Rules:\n"
                "- 'How To Win' is the MOST IMPORTANT section. Be specific: what to find, "
                "what to interact with, what triggers level completion.\n"
                "- NO coordinates from the old level (layout will be different).\n"
                "- NO filler or generic advice. Every line must be a concrete, tested fact.\n"
                "- Keep it SHORT — under 800 words."
            )},
            {"role": "user", "content": (
                f"# Level {completed_level} Skill (just completed):\n```\n{prev_content}\n```\n\n"
                f"Distill this into a cheat sheet for Level {new_level}. "
                "Focus on the WINNING PROCEDURE — what exactly must the player do to score?"
            )},
        ]

        from arc.config import OPENROUTER_BASE_URL, API_TIMEOUT
        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY", "")
        client = OpenAIClient(
            api_key=api_key,
            base_url=OPENROUTER_BASE_URL,
            timeout=API_TIMEOUT,
        )

        update_tool = [t for t in self._build_tools() if t["function"]["name"] == "update_skill"]

        # Temporarily set current_level to new_level so _handle_update_skill writes to the right dir
        saved_level = self.current_level
        self.current_level = new_level

        for attempt in range(API_RETRIES):
            try:
                create_kwargs: dict[str, Any] = {
                    "model": self._model,
                    "messages": messages,
                    "tools": update_tool,
                    "tool_choice": {"type": "function", "function": {"name": "update_skill"}},
                }
                extra = self._extra_body
                if extra:
                    create_kwargs["extra_body"] = extra
                response = self._create_completion(client, **create_kwargs)
                break
            except (openai.BadRequestError, openai.APIConnectionError,
                    openai.RateLimitError, openai.APITimeoutError,
                    TimeoutError) as e:
                logger.warning("Level-up summary API error on attempt %d: %s", attempt + 1, e)
                if attempt == API_RETRIES - 1:
                    self.current_level = saved_level
                    return
                time.sleep(2 ** attempt)
        else:
            self.current_level = saved_level
            return

        self.current_level = saved_level  # restore before handling
        self.track_tokens(response.usage.total_tokens if response.usage else 0)
        if not response.choices:
            return

        message = response.choices[0].message
        if message.tool_calls:
            tc = message.tool_calls[0]
            try:
                data = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                data = {}
            content = data.get("content", "")
            if content and len(content.strip()) > 10:
                # Write to SKILL.base.md (template — never overwritten by agent)
                base_dir = skill_base / f"level{new_level}"
                base_dir.mkdir(parents=True, exist_ok=True)
                base_path = base_dir / "SKILL.base.md"
                base_path.write_text(content, encoding="utf-8")
                logger.info("Level-up template written for level %d: %s (%d chars)",
                            new_level, base_path, len(content))
            else:
                logger.warning("Level-up summary: content too short (%d chars)", len(content))
        else:
            logger.warning("Level-up summary: LLM did not return tool call")

    def _handle_update_skill(self, args_json: str) -> str:
        """Write the agent's evolved skill file to disk (per-level)."""
        try:
            data = json.loads(args_json) if args_json else {}
        except json.JSONDecodeError:
            return "Error: invalid JSON"
        content = data.get("content", "")
        if not content or len(content.strip()) < 10:
            return "Error: content too short, must be at least 10 chars"

        skill_dir = Path(__file__).parent / "skills" / f"arc-{self.game_id}" / f"level{self.current_level}"
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_path = skill_dir / "SKILL.md"

        # Protect against content regression — don't overwrite good content with junk
        if skill_path.is_file():
            old = skill_path.read_text(encoding="utf-8")
            if len(old) > 200 and len(content) < len(old) * 0.3:
                logger.warning("Skill update rejected: new (%d chars) is <30%% of old (%d chars)",
                               len(content), len(old))
                return (f"Error: update rejected — new content ({len(content)} chars) "
                        f"is too short compared to existing ({len(old)} chars). "
                        "Include ALL existing knowledge plus new discoveries.")
            # Backup old skill before overwriting
            if len(old.strip()) >= 10:
                from datetime import datetime
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                step = len(self.current_steps)
                backup_name = f"SKILL.step{step}.{ts}.md"
                (skill_dir / backup_name).write_text(old, encoding="utf-8")
                logger.info("Skill backup: %s", backup_name)

        skill_path.write_text(content, encoding="utf-8")
        logger.info("Skill updated (level %d): %s (%d chars)", self.current_level, skill_path, len(content))
        return f"Skill saved for level {self.current_level} ({len(content)} chars)"

    def _handle_load_skill(self, args_json: str) -> str:
        """Load a thinking tool's full SKILL.md content."""
        try:
            data = json.loads(args_json) if args_json else {}
        except json.JSONDecodeError:
            return "Error: invalid JSON"
        name = data.get("name", "").strip()

        if not name or name.lower() == "list":
            from arc.skills_loader import load_skill_summaries
            summaries = load_skill_summaries()
            if not summaries:
                return "No skills available."
            lines = ["Available skills:"]
            for dir_name, skill_name, desc in summaries:
                lines.append(f"  - {dir_name}: {skill_name} — {desc}")
            return "\n".join(lines)

        from arc.skills_loader import load_single_skill
        try:
            matched_name, content = load_single_skill(name)
            if len(content) > 8000:
                content = content[:8000] + "\n\n... [truncated at 8000 chars]"
            return f"# Skill: {matched_name}\n\n{content}"
        except ValueError as e:
            return f"Error: {e}"

    def _handle_run_code(self, args_json: str) -> str:
        """Execute Python code with game state variables in a sandboxed environment."""
        try:
            data = json.loads(args_json) if args_json else {}
        except json.JSONDecodeError:
            return "Error: invalid JSON"
        code = data.get("code", "").strip()
        if not code:
            return "Error: empty code"

        # Build namespace with game state
        latest = self.frames[-1] if self.frames else None
        namespace: dict[str, Any] = {
            "grid": latest.frame[0] if latest and latest.frame else [],
            "grids": latest.frame if latest and latest.frame else [],
            "score": self._last_score,
            "step_count": len(self.current_steps),
            "action_history": [
                {"action": s.get("action", "?"), "effect": s.get("effect", "?"), "score": s.get("score", 0)}
                for s in self.current_steps
            ],
        }

        # Restricted builtins
        import builtins
        safe_builtins = {
            k: getattr(builtins, k) for k in (
                "abs", "all", "any", "bin", "bool", "bytes", "chr", "dict",
                "divmod", "enumerate", "filter", "float", "format", "frozenset",
                "getattr", "hasattr", "hash", "hex", "int", "isinstance",
                "issubclass", "iter", "len", "list", "map", "max", "min",
                "next", "oct", "ord", "pow", "print", "range", "repr",
                "reversed", "round", "set", "slice", "sorted", "str", "sum",
                "tuple", "type", "zip",
            )
        }

        # Restricted import
        _ALLOWED_MODULES = frozenset({
            "math", "collections", "itertools", "functools", "json", "re",
            "heapq", "bisect", "copy", "statistics", "random", "string",
        })

        def _restricted_import(name, *args, **kwargs):
            if name not in _ALLOWED_MODULES:
                raise ImportError(f"Import of '{name}' is not allowed. Allowed: {', '.join(sorted(_ALLOWED_MODULES))}")
            return __builtins__.__import__(name, *args, **kwargs) if hasattr(__builtins__, '__import__') else __import__(name, *args, **kwargs)

        safe_builtins["__import__"] = _restricted_import
        namespace["__builtins__"] = safe_builtins

        # Pre-load saved functions into namespace
        func_dir = Path(__file__).parent / "skills" / f"arc-{self.game_id}" / "functions"
        if func_dir.is_dir():
            for py_file in sorted(func_dir.glob("*.py")):
                try:
                    func_code = py_file.read_text(encoding="utf-8")
                    exec(func_code, namespace)
                except Exception as e:
                    logger.warning("Failed to load function %s: %s", py_file.name, e)

        # Capture stdout
        stdout_capture = io.StringIO()
        result_container: list[str] = []
        error_container: list[str] = []

        def _run():
            import sys
            old_stdout = sys.stdout
            sys.stdout = stdout_capture
            try:
                exec(code, namespace)
                result_container.append(stdout_capture.getvalue())
            except Exception as e:
                result_container.append(stdout_capture.getvalue())
                error_container.append(f"{type(e).__name__}: {e}")
            finally:
                sys.stdout = old_stdout

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        thread.join(timeout=5.0)

        if thread.is_alive():
            return "Error: code execution timed out (5s limit)"

        # Extract and persist user-defined functions
        if not error_container:
            try:
                func_dir.mkdir(parents=True, exist_ok=True)
                tree = ast.parse(code)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        fname = node.name
                        if fname.startswith("_"):
                            continue
                        lines = code.split("\n")
                        func_source = "\n".join(lines[node.lineno - 1 : node.end_lineno])
                        docstring = ast.get_docstring(node) or ""
                        func_path = func_dir / f"{fname}.py"
                        header = f'"""{docstring}"""\n' if docstring else ""
                        func_path.write_text(header + func_source + "\n", encoding="utf-8")
                        logger.info("Saved function: %s -> %s", fname, func_path.name)
            except Exception as e:
                logger.warning("Function extraction failed: %s", e)

        output = result_container[0] if result_container else ""
        if error_container:
            output += f"\n[ERROR] {error_container[0]}"

        if not output.strip():
            output = "(no output — use print() to see results)"

        if len(output) > 4000:
            output = output[:4000] + "\n... [truncated at 4000 chars]"

        return output

    # ------------------------------------------------------------------
    # Action execution
    # ------------------------------------------------------------------

    def _execute_action(self, name: str, args_json: str, reasoning: str = "") -> None:
        """Execute one game action and record the step."""
        try:
            data = json.loads(args_json) if args_json else {}
        except json.JSONDecodeError:
            data = {}

        action = GameAction.from_name(name)
        action.set_data(data)

        # Attach reasoning so it gets sent to the API / scorecard
        if reasoning:
            action.reasoning = {"content": reasoning}

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
        step_record = {
            "action": name,
            "effect": effect,
            "score": curr_score,
        }
        if reasoning:
            step_record["reasoning"] = reasoning
        self.current_steps.append(step_record)

        # Record reasoning to JSONL recording
        if reasoning and hasattr(self, "recorder"):
            self.recorder.record({
                "type": "reasoning",
                "step": self.action_counter,
                "action": name,
                "reasoning": reasoning,
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
        """Reset state for a new attempt, keeping learned knowledge in SKILL.md.

        Note: action_counter is NOT reset — arc env steps are cumulative.
        """
        self.current_steps = []
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
