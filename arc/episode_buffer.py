"""Episode data structures and exploration buffer."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional

import numpy as np


@dataclass
class StepRecord:
    """A single step in a game episode."""
    state_text: str
    action: str
    frame_diff: str
    score_before: int
    score_after: int
    reasoning: str = ""  # LLM's reasoning for this action choice


@dataclass
class GameEpisode:
    """A complete game episode from RESET to WIN/GAME_OVER."""
    game_id: str
    steps: list[StepRecord] = field(default_factory=list)
    success: bool = False
    final_score: int = 0
    total_actions: int = 0
    embedding: Optional[np.ndarray] = None
    step_embeddings: list[np.ndarray] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "game_id": self.game_id,
            "steps": [asdict(s) for s in self.steps],
            "success": self.success,
            "final_score": self.final_score,
            "total_actions": self.total_actions,
            "embedding": self.embedding.tolist() if self.embedding is not None else None,
            "step_embeddings": [e.tolist() for e in self.step_embeddings],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GameEpisode:
        # Backwards-compatible: old checkpoints lack 'reasoning' field
        raw_steps = data.get("steps", [])
        steps = []
        for s in raw_steps:
            s.setdefault("reasoning", "")
            steps.append(StepRecord(**s))
        emb = data.get("embedding")
        step_embs = data.get("step_embeddings", [])
        return cls(
            game_id=data["game_id"],
            steps=steps,
            success=data.get("success", False),
            final_score=data.get("final_score", 0),
            total_actions=data.get("total_actions", 0),
            embedding=np.array(emb, dtype=np.float32) if emb is not None else None,
            step_embeddings=[np.array(e, dtype=np.float32) for e in step_embs],
        )

    def summary(self, max_steps: int = 10) -> str:
        outcome = "SUCCESS" if self.success else "FAILED"
        lines = [
            f"Episode ({outcome}, score={self.final_score}, "
            f"{self.total_actions} actions):"
        ]
        if len(self.steps) > max_steps:
            show = self.steps[:max_steps // 2] + self.steps[-(max_steps // 2):]
        else:
            show = self.steps
        for i, step in enumerate(show):
            marker = ""
            if step.score_after > step.score_before:
                marker = " [SCORE+]"
            elif "no_change" in step.frame_diff:
                marker = " [NO EFFECT]"
            lines.append(f"  Step {i}: {step.action} -> {step.frame_diff}{marker}")
        return "\n".join(lines)


class EpisodeBuffer:
    """Buffer for storing and retrieving game episodes."""

    def __init__(self, capacity: int = 100, emb_dim: int = 512):
        self.capacity = capacity
        self.emb_dim = emb_dim
        self.episodes: list[GameEpisode] = []

    def add(self, episode: GameEpisode) -> None:
        if len(self.episodes) >= self.capacity:
            self.episodes.pop(0)
        self.episodes.append(episode)

    def retrieve(
        self,
        query_emb: np.ndarray,
        k: int = 5,
        success_only: bool = False,
        game_id: Optional[str] = None,
    ) -> list[tuple[GameEpisode, float]]:
        candidates = self.episodes
        if success_only:
            candidates = [e for e in candidates if e.success]
        if game_id is not None:
            candidates = [e for e in candidates if e.game_id == game_id]
        if not candidates:
            return []
        results: list[tuple[GameEpisode, float]] = []
        for ep in candidates:
            if ep.embedding is not None:
                sim = float(np.dot(query_emb, ep.embedding))
                results.append((ep, sim))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:k]

    def get_size(self) -> int:
        return len(self.episodes)

    def get_success_rate(self) -> float:
        if not self.episodes:
            return 0.0
        return sum(1 for e in self.episodes if e.success) / len(self.episodes)

    def clear(self) -> None:
        self.episodes.clear()
