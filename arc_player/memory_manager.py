"""File-based structured memory for ARC game agent.

Memory is organized by game and level:
  memory/{game_id}/
    shared/        — game-wide knowledge (cross-level)
    level1/        — level-specific knowledge
    level2/        — ...

Each scope has subfolders:
  hypotheses/  — unverified ideas
  verified/    — confirmed rules (auto-promoted when confirmed_count >= PROMOTE_THRESHOLD)
  discoveries/ — raw observations
  summaries/   — strategy synthesis
  disproved/   — falsified hypotheses (auto-moved when contradicted_count >= DISPROVE_THRESHOLD)

Evidence tools:
  confirm(filename, evidence)   → +1 confirmed, auto-promote at threshold
  contradict(filename, evidence) → +1 contradicted, auto-disprove at threshold
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

FOLDERS = ("hypotheses", "verified", "discoveries", "summaries", "disproved")
MAX_HYPOTHESES = 10  # Auto-prune oldest when exceeded
MAX_VERIFIED = 10  # Auto-prune oldest verified when exceeded
MAX_SNAPSHOT_PER_FOLDER = 8  # Max files shown in memory snapshot per folder
PROMOTE_THRESHOLD = 2  # Auto-promote to verified/ at this many confirmations
DISPROVE_THRESHOLD = 2  # Auto-move to disproved/ at this many contradictions
MIN_EVIDENCE_LENGTH = 50  # Minimum chars for evidence to be considered valid
REQUIRED_EVIDENCE_KEYWORDS = ("step", "action")  # Must mention step number and action


def _parse_frontmatter(content: str) -> dict[str, str]:
    """Extract YAML frontmatter fields from markdown content."""
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not match:
        return {}
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            fields[key.strip()] = val.strip().strip('"').strip("'")
    return fields


def _set_frontmatter_field(content: str, key: str, value: str | int) -> str:
    """Set or update a field in YAML frontmatter. Creates frontmatter if missing."""
    match = re.match(r"^(---\s*\n)(.*?)(\n---\s*\n)", content, re.DOTALL)
    if not match:
        # No frontmatter — wrap content
        return f"---\n{key}: {value}\n---\n{content}"

    header, fm_body, closer = match.group(1), match.group(2), match.group(3)
    rest = content[match.end():]

    # Check if key already exists
    pattern = re.compile(rf"^({re.escape(key)}:\s*)(.*)$", re.MULTILINE)
    if pattern.search(fm_body):
        fm_body = pattern.sub(rf"\g<1>{value}", fm_body)
    else:
        fm_body += f"\n{key}: {value}"

    return header + fm_body + closer + rest


def _ensure_counters(content: str) -> str:
    """Ensure confirmed_count and contradicted_count exist in frontmatter."""
    meta = _parse_frontmatter(content)
    if "confirmed_count" not in meta:
        content = _set_frontmatter_field(content, "confirmed_count", 0)
    if "contradicted_count" not in meta:
        content = _set_frontmatter_field(content, "contradicted_count", 0)
    return content


def _validate_evidence(evidence: str) -> str | None:
    """Validate evidence quality. Returns error message or None if valid."""
    if not evidence or len(evidence.strip()) < MIN_EVIDENCE_LENGTH:
        return (
            f"REJECTED: Evidence too short (need {MIN_EVIDENCE_LENGTH}+ chars). "
            "Include: step number, action taken, player position (row,col), "
            "nearby objects, and what happened."
        )
    ev_lower = evidence.lower()
    # Must mention a step number
    if "step" not in ev_lower:
        return (
            "REJECTED: Evidence must include STEP NUMBER (e.g. 'Step 25: ...'). "
            "Which step did this observation occur at?"
        )
    # Must include coordinates
    import re
    has_coords = bool(re.search(r'\(\d+[,\s]+\d+\)', evidence))
    if not has_coords:
        return (
            "REJECTED: Evidence must include COORDINATES (e.g. 'player at (35,29)'). "
            "Where was the player? What position was the object at? "
            "Without positions, this evidence is ambiguous."
        )
    return None


class MemoryManager:
    """Manages structured memory files for a specific game, with per-level and shared scopes."""

    def __init__(self, game_id: str, base_dir: Path | None = None, level: int = 1):
        self.game_id = game_id
        self.base = (base_dir or Path(__file__).parent / "memory") / game_id
        self._level = level
        self._ensure_dirs("shared")
        self._ensure_dirs(f"level{level}")

    def _ensure_dirs(self, scope: str) -> None:
        for folder in FOLDERS:
            (self.base / scope / folder).mkdir(parents=True, exist_ok=True)

    def set_level(self, level: int) -> None:
        self._level = level
        self._ensure_dirs(f"level{level}")

    @property
    def current_scope(self) -> str:
        return f"level{self._level}"

    def _resolve_scope(self, scope: str | None) -> str:
        if not scope or scope == "current":
            return self.current_scope
        if scope == "shared":
            return "shared"
        if scope.startswith("level") and scope[5:].isdigit():
            self._ensure_dirs(scope)
            return scope
        return self.current_scope

    # ── List / Read / Write ───────────────────────────────────────────

    def list_files(self, folder: str, scope: str | None = None) -> str:
        """List all .md files in a folder with name, description, and evidence counts."""
        if folder not in FOLDERS:
            return f"Error: invalid folder '{folder}'. Use one of: {', '.join(FOLDERS)}"

        resolved = self._resolve_scope(scope)
        folder_path = self.base / resolved / folder
        if not folder_path.is_dir():
            return f"(empty — no files in {resolved}/{folder}/)"

        files = sorted(folder_path.glob("*.md"))
        if not files:
            return f"(empty — no files in {resolved}/{folder}/)"

        lines = [f"# {resolved}/{folder}/ ({len(files)} files)"]
        for f in files:
            content = f.read_text(encoding="utf-8")
            meta = _parse_frontmatter(content)
            name = meta.get("name", f.stem)
            desc = meta.get("description", "")
            confirmed = meta.get("confirmed_count", "0")
            contradicted = meta.get("contradicted_count", "0")
            score_str = ""
            if confirmed != "0" or contradicted != "0":
                score_str = f" [{confirmed}✓ {contradicted}✗]"
            lines.append(f"- `{f.name}` | {name}{score_str} | {desc}")

        return "\n".join(lines)

    def list_files_parsed(self, folder: str, scope: str | None = None) -> list[dict[str, str]]:
        """List files with parsed metadata (for internal use)."""
        if folder not in FOLDERS:
            return []
        resolved = self._resolve_scope(scope)
        folder_path = self.base / resolved / folder
        if not folder_path.is_dir():
            return []
        result = []
        for f in sorted(folder_path.glob("*.md")):
            content = f.read_text(encoding="utf-8")
            meta = _parse_frontmatter(content)
            result.append({
                "filename": f.name,
                "name": meta.get("name", f.stem),
                "description": meta.get("description", ""),
            })
        return result

    def read_file(self, folder: str, filename: str, scope: str | None = None) -> str:
        if folder not in FOLDERS:
            return f"Error: invalid folder '{folder}'."
        resolved = self._resolve_scope(scope)
        path = self.base / resolved / folder / filename
        if not path.is_file():
            return f"Error: file '{filename}' not found in {resolved}/{folder}/."
        return path.read_text(encoding="utf-8")

    def _find_similar_files(self, folder_path: Path, filename: str) -> list[str]:
        """Find existing files with the same base prefix (e.g., nav_strategy for nav_strategy42).

        Returns list of existing filenames with same prefix, excluding exact match.
        """
        # Extract base prefix: strip trailing digits and underscores
        stem = filename.replace(".md", "")
        prefix = re.sub(r"[\d_]+$", "", stem)
        if not prefix:
            return []

        similar = []
        for f in sorted(folder_path.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True):
            f_stem = f.stem
            if f.name == filename:
                continue
            f_prefix = re.sub(r"[\d_]+$", "", f_stem)
            if f_prefix == prefix:
                similar.append(f.name)
        return similar

    def write_file(self, folder: str, filename: str, content: str, scope: str | None = None) -> str:
        """Write or update a memory file."""
        if folder not in FOLDERS:
            return f"Error: invalid folder '{folder}'."

        # Block direct writes to shared/ — use promote_to_shared
        if scope == "shared":
            return (
                "Error: cannot write directly to shared/. "
                "Use `promote_to_shared` after scoring to promote level knowledge to shared."
            )

        # Block direct writes to verified/ and disproved/ — managed by confirm/contradict
        if folder == "verified":
            return "Error: cannot write directly to verified/. Use `confirm` tool to add evidence; auto-promotes at threshold."
        if folder == "disproved":
            return "Error: cannot write directly to disproved/. Use `contradict` tool to add evidence; auto-disproves at threshold."

        # Sanitize filename
        if not filename.endswith(".md"):
            filename += ".md"
        filename = re.sub(r"[^\w\-.]", "_", filename)

        resolved = self._resolve_scope(scope)
        self._ensure_dirs(resolved)
        path = self.base / resolved / folder / filename
        is_update = path.is_file()

        # Check for similar files and nudge agent to UPDATE instead of creating new ones
        if not is_update and folder in ("hypotheses", "summaries"):
            folder_path = self.base / resolved / folder
            similar = self._find_similar_files(folder_path, filename)
            # Also check verified/ for same-prefix files
            verified_path = self.base / resolved / "verified"
            similar_verified = self._find_similar_files(verified_path, filename) if verified_path.is_dir() else []

            all_similar = similar + [f"(verified) {f}" for f in similar_verified]
            if all_similar:
                # Still write the file, but warn strongly
                nudge = (
                    f"\n⚠️ SIMILAR FILES EXIST: {', '.join(all_similar[:5])}. "
                    f"You should UPDATE an existing file instead of creating new ones. "
                    f"Use the SAME filename to overwrite, or read_memory + update the best existing file. "
                    f"Too many similar files dilute your memory and waste context."
                )
            else:
                nudge = ""
        else:
            nudge = ""

        # For hypotheses and discoveries: always ensure counters exist
        if folder in ("hypotheses", "discoveries"):
            content = _ensure_counters(content)

        path.write_text(content, encoding="utf-8")
        action = "Updated" if is_update else "Created"
        logger.info("Memory %s: %s/%s/%s", action.lower(), resolved, folder, filename)

        # Auto-prune hypotheses
        pruned_msg = ""
        if folder == "hypotheses":
            pruned_msg = self._prune_hypotheses(resolved)

        return f"{action} {resolved}/{folder}/{filename}" + pruned_msg + nudge

    def _prune_hypotheses(self, scope: str) -> str:
        """Move oldest hypotheses to disproved/ when exceeding MAX_HYPOTHESES."""
        folder_path = self.base / scope / "hypotheses"
        if not folder_path.is_dir():
            return ""
        files = sorted(folder_path.glob("*.md"), key=lambda f: f.stat().st_mtime)
        if len(files) <= MAX_HYPOTHESES:
            return ""

        dst_dir = self.base / scope / "disproved"
        to_move = files[: len(files) - MAX_HYPOTHESES]
        moved_names = []
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        for f in to_move:
            moved_names.append(f.name)
            content = f.read_text(encoding="utf-8")
            content += f"\n\n## Auto-pruned ({now})\nRemoved due to age/inactivity (exceeded {MAX_HYPOTHESES} limit).\n"
            (dst_dir / f.name).write_text(content, encoding="utf-8")
            f.unlink()
            logger.info("Pruned hypothesis → disproved/: %s/%s", scope, f.name)

        return f" (auto-pruned {len(moved_names)} old hypotheses: {', '.join(moved_names)})"

    def _prune_verified(self, scope: str) -> str:
        """Remove oldest verified files when exceeding MAX_VERIFIED.

        Unlike hypotheses, pruned verified files are deleted (not moved to disproved)
        since they already served their purpose.
        """
        folder_path = self.base / scope / "verified"
        if not folder_path.is_dir():
            return ""
        files = sorted(folder_path.glob("*.md"), key=lambda f: f.stat().st_mtime)
        if len(files) <= MAX_VERIFIED:
            return ""

        to_remove = files[: len(files) - MAX_VERIFIED]
        removed_names = []
        for f in to_remove:
            removed_names.append(f.name)
            f.unlink()
            logger.info("Pruned old verified: %s/%s", scope, f.name)

        return f" (auto-pruned {len(removed_names)} old verified: {', '.join(removed_names)})"

    # ── Evidence Tools ─────────────────────────────────────────────────

    def _find_file(self, filename: str, scope: str | None = None) -> tuple[Path, str] | None:
        """Find a file across hypotheses, discoveries, and verified folders.
        Returns (path, folder_name) or None.
        """
        resolved = self._resolve_scope(scope)
        for folder in ("hypotheses", "discoveries", "verified"):
            path = self.base / resolved / folder / filename
            if path.is_file():
                return path, folder
        return None

    def confirm(self, filename: str, evidence: str, scope: str | None = None) -> str:
        """Add supporting evidence to a hypothesis/discovery. Auto-promotes to verified/ at threshold.

        Args:
            filename: File to confirm (searches hypotheses/, discoveries/, verified/)
            evidence: Specific observation supporting this (coordinates, colors, what happened)
        """
        rejection = _validate_evidence(evidence)
        if rejection:
            return rejection

        resolved = self._resolve_scope(scope)
        found = self._find_file(filename, scope)
        if not found:
            return f"Error: '{filename}' not found in {resolved}/hypotheses/, discoveries/, or verified/."

        path, folder = found
        content = path.read_text(encoding="utf-8")
        content = _ensure_counters(content)

        meta = _parse_frontmatter(content)
        confirmed = int(meta.get("confirmed_count", "0"))

        # Already verified — reject further confirmations, redirect to unverified work
        if folder == "verified":
            # Count unverified hypotheses to nudge agent
            unverified = []
            for check_folder in ("hypotheses", "discoveries"):
                check_path = self.base / resolved / check_folder
                if check_path.is_dir():
                    unverified.extend(f.name for f in check_path.glob("*.md"))
            nudge = ""
            if unverified:
                nudge = (
                    f" You have {len(unverified)} UNVERIFIED files: {', '.join(unverified[:5])}. "
                    "Confirm or contradict THOSE instead — they need evidence more than verified rules do."
                )
            return (
                f"SKIPPED: '{filename}' is already VERIFIED ({confirmed}✓). "
                f"No need to confirm it again.{nudge} "
                "Focus on testing UNVERIFIED hypotheses or forming NEW ones about how to SCORE."
            )

        # Increment confirmed_count
        confirmed += 1
        content = _set_frontmatter_field(content, "confirmed_count", confirmed)

        # Append evidence
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        content += f"\n\n## ✓ Evidence #{confirmed} ({now})\n{evidence}\n"

        path.write_text(content, encoding="utf-8")
        logger.info("Confirmed %s/%s/%s (now %d✓)", resolved, folder, filename, confirmed)

        # Auto-promote: hypotheses/discoveries → verified/ when threshold reached
        result_msg = f"Confirmed '{filename}' [{confirmed}✓]. Evidence recorded."
        if folder in ("hypotheses", "discoveries") and confirmed >= PROMOTE_THRESHOLD:
            dst = self.base / resolved / "verified" / filename
            content = _set_frontmatter_field(content, "verified_at", now)
            dst.write_text(content, encoding="utf-8")
            path.unlink()
            logger.info("Auto-promoted → verified/: %s/%s/%s (%d✓)", resolved, folder, filename, confirmed)
            # Auto-prune old verified files
            pruned = self._prune_verified(resolved)
            result_msg = (
                f"✓ AUTO-PROMOTED '{filename}' from {folder}/ → verified/ ({confirmed} confirmations). "
                f"This is now a VERIFIED rule. Stop confirming it — focus on UNVERIFIED hypotheses or scoring."
            ) + pruned

        return result_msg

    def contradict(self, filename: str, evidence: str, scope: str | None = None) -> str:
        """Add contradicting evidence to a hypothesis/discovery/verified rule.
        Auto-disproves hypotheses at threshold. Demotes verified rules if contradictions exceed confirmations.

        Args:
            filename: File to contradict (searches hypotheses/, discoveries/, verified/)
            evidence: Specific observation contradicting this (coordinates, colors, what happened)
        """
        rejection = _validate_evidence(evidence)
        if rejection:
            return rejection

        resolved = self._resolve_scope(scope)
        found = self._find_file(filename, scope)
        if not found:
            return f"Error: '{filename}' not found in {resolved}/hypotheses/, discoveries/, or verified/."

        path, folder = found
        content = path.read_text(encoding="utf-8")
        content = _ensure_counters(content)

        # Increment contradicted_count
        meta = _parse_frontmatter(content)
        contradicted = int(meta.get("contradicted_count", "0")) + 1
        confirmed = int(meta.get("confirmed_count", "0"))
        content = _set_frontmatter_field(content, "contradicted_count", contradicted)

        # Append evidence
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        content += f"\n\n## ✗ Contradiction #{contradicted} ({now})\n{evidence}\n"

        result_msg = f"Contradicted '{filename}' [{confirmed}✓ {contradicted}✗]. Evidence recorded."

        # Auto-disprove hypotheses/discoveries at threshold
        if folder in ("hypotheses", "discoveries") and contradicted >= DISPROVE_THRESHOLD:
            self._ensure_dirs(resolved)
            dst = self.base / resolved / "disproved" / filename
            content = _set_frontmatter_field(content, "disproved_at", now)
            dst.write_text(content, encoding="utf-8")
            path.unlink()
            logger.info("Auto-disproved → disproved/: %s/%s (%d✗)", resolved, filename, contradicted)
            result_msg = (
                f"✗ AUTO-DISPROVED '{filename}' → disproved/ ({contradicted} contradictions). "
                f"Hypothesis falsified."
            )
        # Demote verified rules if contradictions exceed confirmations
        elif folder == "verified" and contradicted > confirmed:
            dst = self.base / resolved / "hypotheses" / filename
            content = _set_frontmatter_field(content, "demoted_at", now)
            dst.write_text(content, encoding="utf-8")
            path.unlink()
            logger.info("Demoted verified → hypotheses: %s/%s (%d✗ > %d✓)", resolved, filename, contradicted, confirmed)
            result_msg = (
                f"⚠ DEMOTED '{filename}' → hypotheses/ ({contradicted}✗ > {confirmed}✓). "
                f"Rule needs re-evaluation."
            )
        else:
            path.write_text(content, encoding="utf-8")
            logger.info("Contradicted %s/%s/%s (now %d✗)", resolved, folder, filename, contradicted)

        return result_msg

    # ── Cross-Level Promotion ─────────────────────────────────────────

    def promote_to_shared(self, folder: str, filename: str, source_scope: str | None = None) -> str:
        """Copy a file from a level scope to shared/ scope."""
        if folder not in FOLDERS:
            return f"Error: invalid folder '{folder}'."

        resolved_src = self._resolve_scope(source_scope)
        if resolved_src == "shared":
            return "Error: source scope cannot be 'shared'."

        src_path = self.base / resolved_src / folder / filename
        if not src_path.is_file():
            return f"Error: '{filename}' not found in {resolved_src}/{folder}/."

        self._ensure_dirs("shared")
        dst_path = self.base / "shared" / folder / filename
        content = src_path.read_text(encoding="utf-8")

        if dst_path.is_file():
            logger.info("Overwriting shared/%s/%s with version from %s", folder, filename, resolved_src)

        dst_path.write_text(content, encoding="utf-8")
        logger.info("Promoted to shared: %s/%s/%s → shared/%s/%s", resolved_src, folder, filename, folder, filename)
        return f"Promoted '{filename}' from {resolved_src}/{folder}/ → shared/{folder}/. Available across all levels."

    # ── Delete / Utility ──────────────────────────────────────────────

    def delete_file(self, folder: str, filename: str, scope: str | None = None) -> str:
        if folder not in FOLDERS:
            return f"Error: invalid folder '{folder}'."
        resolved = self._resolve_scope(scope)
        path = self.base / resolved / folder / filename
        if not path.is_file():
            return f"Error: '{filename}' not found in {resolved}/{folder}/."
        path.unlink()
        return f"Deleted {resolved}/{folder}/{filename}."

    def get_memory_snapshot(self) -> str:
        """Compact snapshot of memory across current scope + shared.

        Shows at most MAX_SNAPSHOT_PER_FOLDER files per folder (most recent first).
        Hidden files are indicated with a count.
        Disproved files are never shown (they're archived).
        """
        sections = []

        for scope in ["shared", "current"]:
            scope_label = "Game-wide (shared)" if scope == "shared" else f"Level {self._level}"
            scope_lines = []

            for folder in ("verified", "hypotheses", "discoveries"):
                resolved = self._resolve_scope(scope)
                folder_path = self.base / resolved / folder
                if not folder_path.is_dir():
                    continue
                # Sort by modification time, newest first
                files = sorted(folder_path.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
                if not files:
                    continue

                # Show only the most recent files
                shown = files[:MAX_SNAPSHOT_PER_FOLDER]
                hidden = len(files) - len(shown)

                for f in shown:
                    content = f.read_text(encoding="utf-8")
                    meta = _parse_frontmatter(content)
                    name = meta.get("name", f.stem)
                    desc = meta.get("description", "")
                    confirmed = meta.get("confirmed_count", "0")
                    contradicted = meta.get("contradicted_count", "0")
                    score_str = f" [{confirmed}✓ {contradicted}✗]" if confirmed != "0" or contradicted != "0" else ""
                    scope_lines.append(f"  {folder}/{f.name}{score_str} | {name} | {desc}")

                if hidden > 0:
                    scope_lines.append(f"  ... +{hidden} older {folder} files (use list_memory to see all)")

            if scope_lines:
                sections.append(f"**{scope_label}:**\n" + "\n".join(scope_lines))

        if not sections:
            return ""
        return "\n".join(sections)
