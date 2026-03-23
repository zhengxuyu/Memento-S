"""Persistent game statistics tracker.

Accumulates steps, LLM calls, tokens, resets, and episodes across runs.
Stored as a single JSON file organized by game_id and level.
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _empty_level() -> dict[str, Any]:
    return {
        "total_steps": 0,
        "total_llm_calls": 0,
        "total_tokens": 0,
        "llm_calls": [],
        "episodes": 0,
        "resets": 0,
        "level_ups": 0,
        "game_overs": 0,
        "max_actions_hits": 0,
        "last_updated": "",
    }


class GameStats:
    """Load/save cumulative game statistics from a JSON file."""

    def __init__(self, stats_file: str) -> None:
        self._path = Path(stats_file)
        self._data: dict[str, Any] = self._load()

    # ---- persistence ----

    def _load(self) -> dict[str, Any]:
        if self._path.is_file():
            try:
                return json.loads(self._path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning("game_stats: failed to load %s: %s", self._path, e)
        return {}

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(
                dir=str(self._path.parent), suffix=".tmp"
            )
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
                f.write("\n")
            os.replace(tmp, str(self._path))
        except Exception as e:
            logger.warning("game_stats: failed to save: %s", e)

    # ---- helpers ----

    def _ensure(self, game_id: str, level: int) -> dict[str, Any]:
        """Return the per-level entry, creating it if needed."""
        game = self._data.setdefault(game_id, {})
        key = f"level{level}"
        if key not in game:
            game[key] = _empty_level()
        if "global" not in game:
            game["global"] = _empty_level()
        return game[key]

    def _ts(self) -> str:
        return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    # ---- public API ----

    def record_step(self, game_id: str, level: int) -> None:
        entry = self._ensure(game_id, level)
        entry["total_steps"] += 1
        entry["last_updated"] = self._ts()
        g = self._data[game_id]["global"]
        g["total_steps"] += 1
        g["last_updated"] = entry["last_updated"]
        self._save()

    def record_llm_call(self, game_id: str, level: int, tokens: int, step: int) -> None:
        entry = self._ensure(game_id, level)
        entry["total_llm_calls"] += 1
        entry["total_tokens"] += tokens
        entry["llm_calls"].append({
            "timestamp": self._ts(),
            "tokens": tokens,
            "step": step,
        })
        entry["last_updated"] = entry["llm_calls"][-1]["timestamp"]
        g = self._data[game_id]["global"]
        g["total_llm_calls"] += 1
        g["total_tokens"] += tokens
        g["last_updated"] = entry["last_updated"]
        self._save()

    def record_episode_end(self, game_id: str, level: int, result: str) -> None:
        entry = self._ensure(game_id, level)
        entry["episodes"] += 1
        ts = self._ts()
        entry["last_updated"] = ts
        if result == "game_over":
            entry["game_overs"] += 1
        elif result == "max_actions":
            entry["max_actions_hits"] += 1
        elif result == "level_up":
            entry["level_ups"] += 1
        elif result == "win":
            entry["level_ups"] += 1
        # resets tracked via record_step on RESET actions
        g = self._data[game_id]["global"]
        g["episodes"] += 1
        g["last_updated"] = ts
        self._save()

    def get_summary(self, game_id: Optional[str] = None, level: Optional[int] = None) -> dict[str, Any]:
        if game_id and level is not None:
            return self._data.get(game_id, {}).get(f"level{level}", {})
        if game_id:
            return self._data.get(game_id, {})
        return self._data
