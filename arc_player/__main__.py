"""CLI entry point: python -m arc_player"""
from __future__ import annotations

import argparse
import atexit
import logging
import os
import signal

from dotenv import load_dotenv

load_dotenv()


def main() -> None:
    parser = argparse.ArgumentParser(description="ARC-AGI-3 Game Player")
    parser.add_argument("-g", "--game", type=str, required=True, help="Game ID (e.g., ls20)")
    parser.add_argument("--model", type=str, default=None, help="LLM model override")
    parser.add_argument("--url", type=str, default="http://localhost:8000", help="ARC API URL")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--card-id", type=str, default=None, help="Reuse existing scorecard")
    parser.add_argument("-t", "--tags", type=str, default=None, help="Comma-separated scorecard tags")
    parser.add_argument("--shortcut", action="store_true", help="Replay solved levels without LLM")
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")
    logger = logging.getLogger(__name__)

    if args.model:
        os.environ["ARC_AGI_MODEL"] = args.model

    from arc_agi import Arcade, OperationMode

    recordings_dir = os.environ.get("RECORDINGS_DIR", "").strip() or "recordings"
    os.makedirs(recordings_dir, exist_ok=True)

    arcade = Arcade(recordings_dir=recordings_dir, operation_mode=OperationMode.ONLINE)

    tags = [t.strip() for t in args.tags.split(",")] if args.tags else ["arc-player"]
    card_id = args.card_id or arcade.open_scorecard(tags=tags)
    logger.info("Scorecard: %s", card_id)

    arc_env = arcade.make(args.game, save_recording=True, scorecard_id=card_id)

    from arc_player.agent import ArcPlayer

    agent = ArcPlayer(
        game_id=args.game,
        arc_env=arc_env,
        arcade=arcade,
        model=args.model or "",
        scorecard_id=card_id,
        shortcut=args.shortcut,
    )

    _closed = False

    def _close():
        nonlocal _closed
        if _closed:
            return
        _closed = True
        try:
            result = arcade.close_scorecard(card_id)
            if result:
                logger.info("Scorecard closed: score=%.1f", result.score)
        except Exception as e:
            logger.warning("Scorecard close failed: %s", e)

    atexit.register(_close)

    def _shutdown(signum, _frame):
        logger.info("Signal %s, shutting down...", signum)
        _close()
        raise SystemExit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        agent.main()
    finally:
        _close()


if __name__ == "__main__":
    main()
