"""CLI entry point: python -m arc"""
from __future__ import annotations

import argparse
import atexit
import logging
import os
import signal
import shutil

from dotenv import load_dotenv

load_dotenv()  # Load .env before anything reads os.environ


def _reset_skills() -> None:
    """Reset SKILL.md to template."""
    skills_dir = os.path.join(os.path.dirname(__file__), "skills", "arc_game_playing")
    template = os.path.join(skills_dir, "SKILL.template.md")
    target = os.path.join(skills_dir, "SKILL.md")
    if os.path.isfile(template):
        shutil.copy2(template, target)

    # Remove skill versions
    versions_dir = os.path.join(skills_dir, "skill_versions")
    if os.path.isdir(versions_dir):
        shutil.rmtree(versions_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="ARC-AGI-3 ReactAgent")
    parser.add_argument("-g", "--game", type=str, help="Game ID to play")
    parser.add_argument("--model", type=str, default=None, help="LLM model override")
    parser.add_argument("--retries", type=int, default=None, help="Max retries")
    parser.add_argument("--url", type=str, default="http://localhost:8000", help="ARC API URL")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--reset-skills", action="store_true", help="Reset skills to template")
    parser.add_argument("--no-memory", action="store_true", help="Disable episode memory")
    parser.add_argument("--memory-warmup", type=int, default=None, help="Cold start episodes before few-shot kicks in (default: 3)")
    parser.add_argument("--shortcut", action="store_true", help="Replay solved levels without LLM calls")
    parser.add_argument("--card-id", type=str, default=None, help="Use existing scorecard ID")
    parser.add_argument("-t", "--tags", type=str, default=None, help="Comma-separated scorecard tags")
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

    if not args.game:
        parser.error("Provide a game ID with -g")

    from arc.react_agent import ReactAgent
    from arc_agi import Arcade

    recordings_dir = os.environ.get("RECORDINGS_DIR", "").strip() or "recordings"
    os.makedirs(recordings_dir, exist_ok=True)

    logger = logging.getLogger(__name__)

    from arc_agi import OperationMode
    # ONLINE mode: scorecard + game actions go through the API, scores visible on website
    arcade = Arcade(recordings_dir=recordings_dir, operation_mode=OperationMode.ONLINE)

    # Scorecard: use provided card_id or create a new one via API
    tags = [t.strip() for t in args.tags.split(",")] if args.tags else ["agent", "react"]
    card_id = args.card_id or arcade.open_scorecard(tags=tags)
    logger.info("Using scorecard: %s", card_id)

    memory_kwargs = {}
    if args.no_memory:
        memory_kwargs["memory"] = False
    if args.memory_warmup is not None:
        memory_kwargs["memory_warmup"] = args.memory_warmup

    arc_env = arcade.make(args.game, save_recording=True, scorecard_id=card_id)

    agent = ReactAgent(
        card_id=card_id,
        game_id=args.game,
        agent_name="react",
        ROOT_URL=args.url,
        record=True,
        arc_env=arc_env,
        arcade=arcade,
        shortcut=args.shortcut,
        **memory_kwargs,
    )

    _scorecard_closed = False

    def _close_scorecard():
        nonlocal _scorecard_closed
        if _scorecard_closed:
            return
        _scorecard_closed = True
        logger.info("Closing scorecard %s ...", card_id)
        try:
            result = arcade.close_scorecard(card_id)
            if result:
                logger.info("Scorecard submitted: score=%.1f", result.score)
            else:
                logger.warning("close_scorecard returned None")
        except Exception as e:
            logger.warning("Scorecard submission failed: %s", e)

    # atexit runs on normal exit and SIGTERM (when Python handles it)
    atexit.register(_close_scorecard)

    def _shutdown(signum, _frame):
        logger.info("Signal %s received, cleaning up...", signum)
        try:
            agent._generate_live_video()
            agent.cleanup()
        except Exception as e:
            logger.warning("Cleanup failed: %s", e)
        _close_scorecard()
        raise SystemExit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        agent.main()
    finally:
        _close_scorecard()


if __name__ == "__main__":
    main()
