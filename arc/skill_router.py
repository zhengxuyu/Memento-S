"""Semantic Skill Router for ARC-AGI-3 agent.

Adapted from Memento-S core/router.py + core/skill_engine/skill_catalog.py.

Instead of routing between *skills* (we only have 2), this routes between
*skill sections* — breaking each SKILL.md into indexed paragraphs and
selecting the top-K most relevant sections based on current game context.

This reduces prompt token usage and focuses the LLM on what matters NOW.

Supports:
- TF-IDF cosine similarity (default, zero-dep)
- BM25 ranking (if rank_bm25 installed)
- Forced sections (always included regardless of score)
- Game-state-aware query building
"""
from __future__ import annotations

import logging
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from arc.config import SKILLS_DIR

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------------
# Stopwords (from Memento-S _ROUTER_STOPWORDS, trimmed)
# -------------------------------------------------------------------------
_STOPWORDS = frozenset(
    "a an the is are was were be been being have has had do does did "
    "will would shall should may might can could of in to for on with "
    "at by from as into through during before after above below between "
    "out up down and but or nor not no so if then else when while "
    "about each its it this that these those he she they them his her "
    "your you we our my me i what which who whom how where why all "
    "any both few more most other some such than too very just also "
    "use using used".split()
)


def _tokenize(text: str) -> list[str]:
    """Tokenize for TF-IDF / BM25 indexing."""
    raw = re.findall(r"[a-z0-9]+", str(text or "").lower())
    return [tok for tok in raw if tok not in _STOPWORDS and len(tok) > 1]


# -------------------------------------------------------------------------
# Data structures
# -------------------------------------------------------------------------

@dataclass
class SkillSection:
    """One indexed section from a SKILL.md file."""
    skill_name: str       # e.g. "arc_game_playing"
    heading: str          # e.g. "## Common Game Patterns"
    content: str          # Full text of the section
    tokens: list[str]     # Tokenized heading + content
    is_forced: bool       # Always include in routing results
    char_count: int = 0


@dataclass
class _TfIdfIndex:
    """Pre-computed TF-IDF vectors for all sections."""
    vocab: dict[str, int] = field(default_factory=dict)
    idf: dict[str, float] = field(default_factory=dict)
    doc_tfidf: list[dict[int, float]] = field(default_factory=list)  # per-doc sparse vector
    doc_norms: list[float] = field(default_factory=list)


# -------------------------------------------------------------------------
# Forced sections: always included regardless of semantic score
# -------------------------------------------------------------------------

# These headings are ALWAYS injected (critical at every step)
_FORCED_HEADING_PATTERNS = [
    "Game Basics",
    "Core Loop",
    "Reasoning Template",
    "Discovered Knowledge",
    "Grid Overview",
    "Object Lists",
    "Frame Changes",
]


# -------------------------------------------------------------------------
# SkillRouter
# -------------------------------------------------------------------------

class SkillRouter:
    """Semantic section-level routing for ARC-AGI-3 skills.

    Indexes each section of each SKILL.md and selects top-K most relevant
    sections based on current game context using TF-IDF / BM25.
    """

    def __init__(
        self,
        skills_dir: Optional[str] = None,
        top_k: int = 8,
        forced_headings: Optional[list[str]] = None,
    ):
        self._skills_dir = Path(skills_dir or SKILLS_DIR)
        self.top_k = top_k
        self._forced_patterns = forced_headings or _FORCED_HEADING_PATTERNS
        self._sections: list[SkillSection] = []
        self._tfidf: Optional[_TfIdfIndex] = None
        self._bm25 = None  # rank_bm25.BM25Okapi if available
        self._indexed = False

    # -----------------------------------------------------------------
    # Index building
    # -----------------------------------------------------------------

    def build_index(self) -> int:
        """Scan all SKILL.md files, parse into sections, build TF-IDF index.

        Returns the number of sections indexed.
        """
        self._sections = []
        self._tfidf = None
        self._bm25 = None

        # Find all SKILL.md files
        dirs = [self._skills_dir]
        if not self._skills_dir.is_absolute():
            dirs = [Path.cwd() / self._skills_dir]

        for base in dirs:
            if not base.is_dir():
                continue
            for sub in sorted(base.iterdir()):
                if not sub.is_dir():
                    continue
                for fname in ("SKILL.md", "skill.md"):
                    f = sub / fname
                    if f.is_file():
                        self._parse_skill_file(sub.name, f)
                        break

        if not self._sections:
            logger.warning("SkillRouter: no sections found in %s", self._skills_dir)
            return 0

        self._build_tfidf_index()
        self._try_build_bm25_index()
        self._indexed = True
        logger.info(
            "SkillRouter: indexed %d sections from %s",
            len(self._sections), self._skills_dir,
        )
        return len(self._sections)

    def _parse_skill_file(self, skill_name: str, path: Path) -> None:
        """Parse a SKILL.md into sections split by ## headings."""
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            logger.warning("Could not read %s: %s", path, e)
            return

        # Strip YAML frontmatter
        text = re.sub(r"^---\s*\n.*?\n---\s*\n?", "", text, count=1, flags=re.DOTALL)

        # Split by ## headings (keep heading with content)
        parts = re.split(r"(?=^## )", text, flags=re.MULTILINE)

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # Extract heading
            heading_match = re.match(r"^(#{1,4})\s+(.+?)$", part, re.MULTILINE)
            if heading_match:
                heading = heading_match.group(2).strip()
            else:
                heading = part[:60].strip()

            # Check if forced
            is_forced = any(
                pat.lower() in heading.lower()
                for pat in self._forced_patterns
            )

            tokens = _tokenize(f"{skill_name} {heading} {part}")

            self._sections.append(SkillSection(
                skill_name=skill_name,
                heading=heading,
                content=part,
                tokens=tokens,
                is_forced=is_forced,
                char_count=len(part),
            ))

    def _build_tfidf_index(self) -> None:
        """Build TF-IDF index (Memento-S style)."""
        n_docs = len(self._sections)
        if n_docs == 0:
            return

        # Collect vocabulary and document frequencies
        doc_freq: dict[str, int] = {}
        for sec in self._sections:
            for tok in set(sec.tokens):
                doc_freq[tok] = doc_freq.get(tok, 0) + 1

        # Build vocab (all tokens)
        vocab = {tok: idx for idx, tok in enumerate(sorted(doc_freq.keys()))}

        # Compute IDF
        idf: dict[str, float] = {}
        for tok, freq in doc_freq.items():
            idf[tok] = math.log((1 + n_docs) / (1 + freq)) + 1.0

        # Compute TF-IDF vectors per document
        doc_tfidf: list[dict[int, float]] = []
        doc_norms: list[float] = []

        for sec in self._sections:
            tf = Counter(sec.tokens)
            vec: dict[int, float] = {}
            for tok, count in tf.items():
                if tok in vocab:
                    w = (1 + math.log(count)) * idf.get(tok, 1.0)
                    vec[vocab[tok]] = w
            norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
            doc_tfidf.append(vec)
            doc_norms.append(norm)

        self._tfidf = _TfIdfIndex(
            vocab=vocab, idf=idf,
            doc_tfidf=doc_tfidf, doc_norms=doc_norms,
        )

    def _try_build_bm25_index(self) -> None:
        """Build BM25 index if rank_bm25 is available."""
        try:
            from rank_bm25 import BM25Okapi
            corpus = [sec.tokens for sec in self._sections]
            self._bm25 = BM25Okapi(corpus)
        except ImportError:
            self._bm25 = None

    # -----------------------------------------------------------------
    # Routing: select top-K sections for current game context
    # -----------------------------------------------------------------

    def route(
        self,
        game_context: str,
        top_k: Optional[int] = None,
        method: str = "auto",
    ) -> str:
        """Select top-K relevant skill sections and format for prompt injection.

        Args:
            game_context: Text describing current game state (used as query).
            top_k: Override default top_k.
            method: "tfidf", "bm25", or "auto" (prefer bm25 if available).

        Returns:
            Formatted string of selected skill sections for system prompt.
        """
        if not self._indexed:
            self.build_index()
        if not self._sections:
            return ""

        k = top_k or self.top_k

        # Choose method
        if method == "auto":
            method = "bm25" if self._bm25 is not None else "tfidf"

        if method == "bm25" and self._bm25 is not None:
            scored = self._score_bm25(game_context)
        else:
            scored = self._score_tfidf(game_context)

        # Apply heading-name bonus (like Memento-S +0.35 for name match)
        for i, (idx, score) in enumerate(scored):
            sec = self._sections[idx]
            bonus = 0.0
            context_lower = game_context.lower()
            # Bonus for heading appearing in context
            heading_tokens = _tokenize(sec.heading)
            overlap = sum(1 for t in heading_tokens if t in context_lower)
            if overlap > 0:
                bonus += min(overlap * 0.05, 0.2)
            scored[i] = (idx, score + bonus)

        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)

        # Collect forced sections
        forced_indices = {
            i for i, sec in enumerate(self._sections) if sec.is_forced
        }

        # Build result: top-K scored + forced
        selected_indices: list[int] = []
        for idx, score in scored:
            if len(selected_indices) >= k and idx not in forced_indices:
                break
            if idx not in selected_indices:
                selected_indices.append(idx)

        # Ensure all forced sections are included
        for fi in sorted(forced_indices):
            if fi not in selected_indices:
                selected_indices.append(fi)

        # Format output
        return self._format_sections(selected_indices)

    def _score_tfidf(self, query: str) -> list[tuple[int, float]]:
        """Score all sections against query using TF-IDF cosine similarity."""
        if self._tfidf is None:
            return [(i, 0.0) for i in range(len(self._sections))]

        idx = self._tfidf
        q_tokens = _tokenize(query)
        q_tf = Counter(q_tokens)

        # Query vector
        q_vec: dict[int, float] = {}
        for tok, count in q_tf.items():
            if tok in idx.vocab:
                w = (1 + math.log(count)) * idx.idf.get(tok, 1.0)
                q_vec[idx.vocab[tok]] = w
        q_norm = math.sqrt(sum(v * v for v in q_vec.values())) or 1.0

        # Cosine similarity with each document
        results: list[tuple[int, float]] = []
        for doc_i in range(len(self._sections)):
            doc_vec = idx.doc_tfidf[doc_i]
            dot = sum(
                q_vec.get(dim, 0.0) * doc_vec.get(dim, 0.0)
                for dim in q_vec
            )
            sim = dot / (q_norm * idx.doc_norms[doc_i])
            results.append((doc_i, sim))

        return results

    def _score_bm25(self, query: str) -> list[tuple[int, float]]:
        """Score all sections against query using BM25."""
        q_tokens = _tokenize(query)
        if not q_tokens or self._bm25 is None:
            return [(i, 0.0) for i in range(len(self._sections))]

        scores = self._bm25.get_scores(q_tokens)
        return [(i, float(s)) for i, s in enumerate(scores)]

    def _format_sections(self, indices: list[int]) -> str:
        """Format selected sections into a single string."""
        parts: list[str] = []
        for idx in indices:
            sec = self._sections[idx]
            parts.append(sec.content)
        return "\n\n".join(parts)

    # -----------------------------------------------------------------
    # Context-aware query building
    # -----------------------------------------------------------------

    @staticmethod
    def build_game_context(
        *,
        game_phase: str = "exploring",
        last_action: str = "",
        action_had_effect: bool = True,
        score_changed: bool = False,
        is_stuck: bool = False,
        is_looping: bool = False,
        is_game_over: bool = False,
        is_new_level: bool = False,
        has_action_mappings: bool = False,
        objects_nearby: list[str] | None = None,
        retry_count: int = 0,
    ) -> str:
        """Build a text query from the current game state for routing.

        This query determines which skill sections are most relevant.
        """
        parts: list[str] = []

        # Phase
        parts.append(f"game phase: {game_phase}")

        # Action result
        if last_action:
            effect = "had effect" if action_had_effect else "no effect wall hit"
            parts.append(f"last action: {last_action} {effect}")
        if score_changed:
            parts.append("score changed level progress")

        # Problems
        if is_stuck:
            parts.append("stuck no score change exploration strategy recovery")
        if is_looping:
            parts.append("loop detected repetitive actions different approach")
        if is_game_over:
            parts.append("game over retry recovery different strategy failure analysis")

        # Level transition
        if is_new_level:
            parts.append("new level transition cross-level learning prerequisites")

        # Action mappings
        if not has_action_mappings:
            parts.append("action mapping discovery test actions directions")
        else:
            parts.append("action mappings confirmed navigation pathfinding")

        # Objects
        if objects_nearby:
            parts.append(f"objects: {' '.join(objects_nearby[:5])}")
            parts.append("interactive object collection prerequisite")

        # Retry
        if retry_count > 0:
            parts.append(f"retry attempt {retry_count} recovery from failure")

        return " ".join(parts)
