"""Multi-game orchestration for ARC-AGI-3 agents."""
from __future__ import annotations

import json
import logging
import os
from threading import Thread
from typing import TYPE_CHECKING, Optional, Type

from arc_agi import Arcade, OperationMode
from arc_agi.scorecard import EnvironmentScorecard

if TYPE_CHECKING:
    from arc.agent_base import Agent

logger = logging.getLogger()


class Swarm:
    """Orchestration for many agents playing many ARC-AGI-3 games."""

    GAMES: list[str]
    ROOT_URL: str
    agent_name: str
    agent_class: Type[Agent]
    threads: list[Thread]
    agents: list[Agent]
    headers: dict[str, str]
    card_id: Optional[str]
    _arc: Arcade

    def __init__(
        self,
        agent_class: Type[Agent],
        agent_name: str,
        ROOT_URL: str,
        games: list[str],
        tags: Optional[list[str]] = None,
        recordings_dir: str = "recordings",
    ) -> None:
        self.GAMES = games
        self.ROOT_URL = ROOT_URL
        self.agent_name = agent_name
        self.agent_class = agent_class
        self.threads = []
        self.agents = []
        self.headers = {
            "X-API-Key": os.getenv("ARC_API_KEY", ""),
            "Accept": "application/json",
        }
        self.tags = list(tags) if tags else ["agent", agent_name]
        self._arc = Arcade(recordings_dir=recordings_dir)

    def main(self) -> Optional[EnvironmentScorecard]:
        """The main orchestration loop."""
        print("***** MAKING SCORECARD")
        self.card_id = self.open_scorecard()

        print(f"***** MAKING ALL AGENTS with card id: {self.card_id}")
        for i in range(len(self.GAMES)):
            g = self.GAMES[i % len(self.GAMES)]
            a = self.agent_class(
                card_id=self.card_id,
                game_id=g,
                agent_name=self.agent_name,
                ROOT_URL=self.ROOT_URL,
                record=True,
                arc_env=self._arc.make(g, scorecard_id=self.card_id),
                tags=self.tags,
            )
            self.agents.append(a)

        for a in self.agents:
            self.threads.append(Thread(target=a.main, daemon=True))

        for t in self.threads:
            t.start()

        for t in self.threads:
            t.join()

        card_id = self.card_id
        scorecard = self.close_scorecard(card_id)
        if scorecard:
            logger.info("--- FINAL SCORECARD REPORT ---")
            logger.info(json.dumps(scorecard.model_dump(), indent=2))

        if card_id:
            if self._arc.operation_mode == OperationMode.ONLINE:
                scorecard_url = f"{self.ROOT_URL}/scorecards/{card_id}"
                logger.info(f"View your scorecard online: {scorecard_url}")

        self.cleanup(scorecard)
        return scorecard

    def open_scorecard(self) -> str:
        return self._arc.open_scorecard(tags=self.tags)

    def close_scorecard(self, card_id: str) -> Optional[EnvironmentScorecard]:
        self.card_id = None
        return self._arc.close_scorecard(card_id)

    def cleanup(self, scorecard: Optional[EnvironmentScorecard] = None) -> None:
        for a in self.agents:
            a.cleanup(scorecard)
