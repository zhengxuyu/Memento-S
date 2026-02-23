"""CLI entry point: python -m arc"""
from __future__ import annotations

import argparse
import logging
import os
import shutil
import sys

from dotenv import load_dotenv

load_dotenv()  # Load .env before anything reads os.environ


def _reset_skills() -> None:
    """Reset skill folder to template, skill_versions, and checkpoints."""
    from arc.config import CHECKPOINT_DIR

    # Reset SKILL.md to template
    skills_dir = os.path.join(os.path.dirname(__file__), "skills", "arc_game_playing")
    template = os.path.join(skills_dir, "SKILL.template.md")
    target = os.path.join(skills_dir, "SKILL.md")
    if os.path.isfile(template):
        shutil.copy2(template, target)

    # Remove skill versions
    versions_dir = os.path.join(skills_dir, "skill_versions")
    if os.path.isdir(versions_dir):
        shutil.rmtree(versions_dir)

    # Remove checkpoints
    if os.path.isdir(CHECKPOINT_DIR):
        shutil.rmtree(CHECKPOINT_DIR)


def main() -> None:
    parser = argparse.ArgumentParser(description="ARC-AGI-3 ReactBufferAgent")
    parser.add_argument("-g", "--game", type=str, help="Game ID to play")
    parser.add_argument("--games", type=str, nargs="+", help="Multiple game IDs")
    parser.add_argument("--model", type=str, default=None, help="LLM model override")
    parser.add_argument("--retries", type=int, default=None, help="Max retries")
    parser.add_argument("--url", type=str, default="http://localhost:8000", help="ARC API URL")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--reset-skills", action="store_true", help="Reset skill folder to template before starting")
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")

    if args.reset_skills:
        _reset_skills()
        logging.info("Skills reset to template")

    if args.model:
        os.environ["ARC_AGI_MODEL"] = args.model
    if args.retries is not None:
        os.environ["ARC_MAX_RETRIES"] = str(args.retries)

    game_ids = args.games or ([args.game] if args.game else None)
    if not game_ids:
        parser.error("Provide at least one game ID with -g or --games")

    from arc.react_agent import ReactBufferAgent

    recordings_dir = os.environ.get("RECORDINGS_DIR", "").strip() or "recordings"
    os.makedirs(recordings_dir, exist_ok=True)

    if len(game_ids) == 1:
        # Single game mode
        from arc_agi import Arcade
        arcade = Arcade(recordings_dir=recordings_dir)
        agent = ReactBufferAgent(
            card_id="",
            game_id=game_ids[0],
            agent_name="reactbuffer",
            ROOT_URL=args.url,
            record=True,
            arc_env=arcade.make(game_ids[0], save_recording=True),
        )
        agent.main()
    else:
        # Multi-game swarm mode
        from arc.swarm import Swarm
        swarm = Swarm(
            agent_class=ReactBufferAgent,
            agent_name="reactbuffer",
            ROOT_URL=args.url,
            games=game_ids,
            recordings_dir=recordings_dir,
        )
        swarm.main()


if __name__ == "__main__":
    main()
