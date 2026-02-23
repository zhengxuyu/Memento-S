"""ARC-specific configuration and constants."""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw.strip())
    except Exception:
        return default

def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}

# LLM (OpenRouter)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY", "")
OPENROUTER_BASE_URL = (
    (os.getenv("OPENROUTER_BASE_URL") or os.getenv("OPENAI_BASE_URL") or "").strip()
    or "https://openrouter.ai/api/v1"
)
ARC_AGI_MODEL = os.getenv("ARC_AGI_MODEL", "").strip() or "qwen/qwen3.5-397b-a17b"

# ARC environment
ARC_API_KEY = os.getenv("ARC_API_KEY", "")
RECORDINGS_DIR = os.getenv("RECORDINGS_DIR", "")
CHECKPOINT_DIR = os.getenv("CHECKPOINT_DIR", "checkpoints")
SKILLS_DIR = os.getenv("SKILLS_DIR", str(PROJECT_ROOT / "skills"))

# VLM
INLINE_VLM = (os.getenv("INLINE_VLM") or "off").strip().lower()

# Replay
SKIP_REPLAY = os.getenv("SKIP_REPLAY", "").strip()

# Agent constants
MAX_RETRIES = _env_int("ARC_MAX_RETRIES", 5)
MAX_ACTIONS = _env_int("ARC_MAX_ACTIONS", 300)
MESSAGE_LIMIT = _env_int("ARC_MESSAGE_LIMIT", 20)
BUFFER_CAPACITY = _env_int("ARC_BUFFER_CAPACITY", 100)
NUM_RETRIEVE = _env_int("ARC_NUM_RETRIEVE", 3)
EMB_DIM = _env_int("ARC_EMB_DIM", 512)
CHECKPOINT_INTERVAL = _env_int("ARC_CHECKPOINT_INTERVAL", 5)
API_TIMEOUT = _env_int("ARC_API_TIMEOUT", 120)
API_RETRIES = _env_int("ARC_API_RETRIES", 5)

# Skill evolution
EVOLVE_THRESHOLD = _env_int("ARC_EVOLVE_THRESHOLD", 3)

# Semantic skill routing (Memento-S)
ROUTER_TOP_K = _env_int("ARC_ROUTER_TOP_K", 8)
ROUTER_ENABLED = _env_flag("ARC_ROUTER_ENABLED", True)

# Knowledge sections in arc_game_playing/SKILL.md
KNOWLEDGE_HEADERS = {
    "action_mappings": "### Action Mappings",
    "game_rules": "### Game Rules",
    "level_strategies": "### Level Strategies",
    "object_roles": "### Object Roles",
    "tips": "### Tips",
}
