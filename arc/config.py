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

# LLM (OpenRouter)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY", "")
OPENROUTER_BASE_URL = (
    (os.getenv("OPENROUTER_BASE_URL") or os.getenv("OPENAI_BASE_URL") or "").strip()
    or "https://openrouter.ai/api/v1"
)
ARC_AGI_MODEL = os.getenv("ARC_AGI_MODEL", "").strip() or "openai/gpt-5.4-mini"

# ARC environment
ARC_API_KEY = os.getenv("ARC_API_KEY", "")
RECORDINGS_DIR = os.getenv("RECORDINGS_DIR", "")
SKILLS_DIR = os.getenv("SKILLS_DIR", str(PROJECT_ROOT / "skills"))

# Agent constants
MAX_RETRIES = _env_int("ARC_MAX_RETRIES", 5)
MAX_ACTIONS = _env_int("ARC_MAX_ACTIONS", 0)  # 0 = unlimited
MESSAGE_LIMIT = _env_int("ARC_MESSAGE_LIMIT", 20)
API_TIMEOUT = _env_int("ARC_API_TIMEOUT", 120)
API_RETRIES = _env_int("ARC_API_RETRIES", 5)

# Episode memory
MEMORY_DIR = os.getenv("ARC_MEMORY_DIR", str(PROJECT_ROOT.parent / "memory"))
MEMORY_WARMUP = _env_int("ARC_MEMORY_WARMUP", 3)  # cold start: no few-shot for first N episodes

# Knowledge sections in SKILL.md
KNOWLEDGE_HEADERS = {
    "action_mappings": "### Action Mappings",
    "game_rules": "### Game Rules",
    "level_strategies": "### Level Strategies",
    "object_roles": "### Object Roles",
    "tips": "### Tips",
}
