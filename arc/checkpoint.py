"""Checkpoint save/load for agent state persistence."""
from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional

import numpy as np

from arc.episode_buffer import GameEpisode, StepRecord, EpisodeBuffer
from arc.episode_embedding import EpisodeEmbedding

logger = logging.getLogger(__name__)


def checkpoint_dir(base: str = "checkpoints") -> Path:
    p = Path(base)
    if not p.is_absolute():
        p = Path.cwd() / p
    p.mkdir(parents=True, exist_ok=True)
    return p


def checkpoint_path(game_id: str, base: str = "checkpoints") -> Path:
    return checkpoint_dir(base) / f"{game_id}.json"


def replays_path(game_id: str, base: str = "checkpoints") -> Path:
    return checkpoint_dir(base) / f"{game_id}.replays.json"


def save_checkpoint(
    game_id: str,
    retry_count: int,
    total_reasoning_tokens: int,
    token_counter: int,
    episode_buffer: EpisodeBuffer,
    current_steps: list[StepRecord],
    current_step_embeddings: list[np.ndarray],
    embedder: EpisodeEmbedding,
    action_effects: dict[str, list[tuple[int, int]]],
    base: str = "checkpoints",
) -> None:
    try:
        current_steps_data = [asdict(s) for s in current_steps]
        current_embs_data = [e.tolist() for e in current_step_embeddings]

        data: dict[str, Any] = {
            "game_id": game_id,
            "timestamp": time.time(),
            "retry_count": retry_count,
            "total_reasoning_tokens": total_reasoning_tokens,
            "token_counter": token_counter,
            "episodes": [ep.to_dict() for ep in episode_buffer.episodes],
            "current_steps": current_steps_data,
            "current_step_embeddings": current_embs_data,
            "embedder": {
                "vocab": embedder.tfidf._vocab,
                "doc_count": embedder.tfidf._doc_count,
                "word_doc_count": embedder.tfidf._word_doc_count,
            },
            "action_effects": {
                k: [list(t) for t in v]
                for k, v in action_effects.items()
            },
        }
        path = checkpoint_path(game_id, base)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.info(
            "Checkpoint saved: %s (%d episodes, %d current steps, retry=%d)",
            path.name, len(episode_buffer.episodes), len(current_steps), retry_count,
        )
    except Exception as e:
        logger.warning("Failed to save checkpoint: %s", e)


def load_checkpoint(
    game_id: str,
    episode_buffer: EpisodeBuffer,
    embedder: EpisodeEmbedding,
    perception_action_effects: dict[str, list[tuple[int, int]]],
    base: str = "checkpoints",
) -> Optional[dict[str, Any]]:
    """Load checkpoint. Returns dict with retry_count, token_counter, etc. or None."""
    path = checkpoint_path(game_id, base)
    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("Failed to read checkpoint %s: %s", path, e)
        return None

    if data.get("game_id") != game_id:
        logger.warning("Checkpoint game_id mismatch: %s != %s", data.get("game_id"), game_id)
        return None

    try:
        # Restore episode buffer
        for ep_data in data.get("episodes", []):
            ep = GameEpisode.from_dict(ep_data)
            episode_buffer.add(ep)

        # Restore embedder vocabulary
        emb_data = data.get("embedder", {})
        if emb_data:
            embedder.tfidf._vocab = emb_data.get("vocab", {})
            embedder.tfidf._doc_count = emb_data.get("doc_count", 0)
            embedder.tfidf._word_doc_count = emb_data.get("word_doc_count", {})

        # Restore perception action effects
        for action_name, pairs in data.get("action_effects", {}).items():
            perception_action_effects[action_name] = [
                (int(p[0]), int(p[1])) for p in pairs
            ]

        # Recover interrupted in-progress episode
        current_steps_data = data.get("current_steps", [])
        if current_steps_data:
            steps = [StepRecord(**s) for s in current_steps_data]
            embs_data = data.get("current_step_embeddings", [])
            step_embs = [np.array(e, dtype=np.float32) for e in embs_data]

            ctx_parts = [f"game:{game_id}", f"actions:{len(steps)}"]
            if steps:
                recent = " ".join(s.action for s in steps[-10:])
                ctx_parts.append(f"recent:{recent}")
            ctx_text = " ".join(ctx_parts)

            interrupted_ep = GameEpisode(
                game_id=game_id,
                steps=steps,
                success=False,
                final_score=steps[-1].score_after if steps else 0,
                total_actions=len(steps),
                embedding=embedder.encode(ctx_text),
                step_embeddings=step_embs,
            )
            episode_buffer.add(interrupted_ep)

        result = {
            "retry_count": data.get("retry_count", 0),
            "total_reasoning_tokens": data.get("total_reasoning_tokens", 0),
            "token_counter": data.get("token_counter", 0),
            "had_current_steps": bool(current_steps_data),
        }
        logger.info(
            "Checkpoint loaded: %s (%d episodes, retry=%d)",
            path.name, len(episode_buffer.episodes), result["retry_count"],
        )
        return result
    except Exception as e:
        logger.warning("Failed to restore checkpoint %s: %s", path, e)
        return None


def save_level_replay(game_id: str, level_num: int, actions: list[str], base: str = "checkpoints") -> None:
    try:
        replays = load_level_replays(game_id, base)
        if level_num not in replays or len(actions) < len(replays[level_num]):
            replays[level_num] = actions
            path = replays_path(game_id, base)
            data = {str(k): v for k, v in replays.items()}
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            logger.info("Saved replay for level %d: %d actions", level_num, len(actions))
    except Exception as e:
        logger.warning("Failed to save level replay: %s", e)


def load_level_replays(game_id: str, base: str = "checkpoints") -> dict[int, list[str]]:
    path = replays_path(game_id, base)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {int(k): v for k, v in data.items()}
    except Exception as e:
        logger.warning("Failed to load level replays: %s", e)
        return {}
