"""Tree-based exploration memory for ARC game agent.

Each node represents one step in the agent's exploration:
  - state: compact description of the world before action
  - action: what the agent did
  - next_state: compact description of the world after action
  - discoveries: list of filenames (raw observations)
  - hypotheses: list of filenames (theories)
  - summaries: list of filenames (strategy synthesis)
  - proofs: list of filenames (evidence for/against hypotheses)

The tree branches on:
  - New episodes (RESET)
  - Score/level-up events
  - Explicit branching by the agent

Default prompt shows the last 3 nodes' full content.
Knowledge artifact fields show only filenames — agent can open them via tools.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TreeNode:
    """A single node in the exploration tree."""
    id: str                          # e.g. "ep0.s5"
    step: int                        # game step number
    parent_id: str | None = None     # parent node id
    children: list[str] = field(default_factory=list)

    # Core state
    state: str = ""                  # compact state before action
    action: str = ""                 # ACTION1-6 or RESET
    next_state: str = ""             # compact state after action
    effect: str = ""                 # moved/blocked/scored/world_changed

    # Knowledge artifact filenames (not content)
    discoveries: list[str] = field(default_factory=list)
    hypotheses: list[str] = field(default_factory=list)
    summaries: list[str] = field(default_factory=list)
    proofs: list[str] = field(default_factory=list)

    # Metadata
    score: int = 0
    level: int = 1
    player_pos: tuple[int, int] | None = None
    world_changed: bool = False

    def to_dict(self) -> dict[str, Any]:
        d = {
            "id": self.id,
            "step": self.step,
            "parent_id": self.parent_id,
            "children": self.children,
            "state": self.state,
            "action": self.action,
            "next_state": self.next_state,
            "effect": self.effect,
            "discoveries": self.discoveries,
            "hypotheses": self.hypotheses,
            "summaries": self.summaries,
            "proofs": self.proofs,
            "score": self.score,
            "level": self.level,
        }
        if self.player_pos:
            d["player_pos"] = list(self.player_pos)
        d["world_changed"] = self.world_changed
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "TreeNode":
        pos = tuple(d["player_pos"]) if d.get("player_pos") else None
        return cls(
            id=d["id"],
            step=d["step"],
            parent_id=d.get("parent_id"),
            children=d.get("children", []),
            state=d.get("state", ""),
            action=d.get("action", ""),
            next_state=d.get("next_state", ""),
            effect=d.get("effect", ""),
            discoveries=d.get("discoveries", []),
            hypotheses=d.get("hypotheses", []),
            summaries=d.get("summaries", []),
            proofs=d.get("proofs", []),
            score=d.get("score", 0),
            level=d.get("level", 1),
            player_pos=pos,
            world_changed=d.get("world_changed", False),
        )

    def compact_str(self, include_artifacts: bool = True) -> str:
        """Compact single-line representation for tree views."""
        pos_str = f"@({self.player_pos[0]},{self.player_pos[1]})" if self.player_pos else ""
        parts = [f"[{self.id}] {self.action}→{self.effect}{pos_str} score={self.score}"]
        if self.world_changed:
            parts.append("🌍")
        if include_artifacts:
            arts = []
            if self.discoveries:
                arts.append(f"D:{','.join(self.discoveries)}")
            if self.hypotheses:
                arts.append(f"H:{','.join(self.hypotheses)}")
            if self.summaries:
                arts.append(f"S:{','.join(self.summaries)}")
            if self.proofs:
                arts.append(f"P:{','.join(self.proofs)}")
            if arts:
                parts.append(" | ".join(arts))
        return " ".join(parts)

    def full_str(self) -> str:
        """Full multi-line representation for the last-3-nodes prompt."""
        lines = [f"── Node {self.id} (step {self.step}, level {self.level}) ──"]
        if self.state:
            lines.append(f"State:  {self.state}")
        lines.append(f"Action: {self.action} → {self.effect}")
        if self.next_state:
            lines.append(f"Result: {self.next_state}")
        if self.world_changed:
            lines.append("🌍 World changed remotely!")

        # Artifacts — filenames only
        if self.discoveries:
            lines.append(f"Discoveries: {', '.join(self.discoveries)}")
        if self.hypotheses:
            lines.append(f"Hypotheses:  {', '.join(self.hypotheses)}")
        if self.summaries:
            lines.append(f"Summaries:   {', '.join(self.summaries)}")
        if self.proofs:
            lines.append(f"Proofs:      {', '.join(self.proofs)}")

        return "\n".join(lines)


class ExplorationTree:
    """Tree-structured exploration memory.

    Provides:
    - add_node(): record a new exploration step
    - get_recent_nodes(n): get the last n nodes on current branch
    - get_branch_path(): full path from root to current node
    - get_subtree(node_id): view children of a node
    - search_nodes(query): find nodes by action/effect/artifact name
    - render_recent(n): render last n nodes for prompt injection
    """

    def __init__(self, save_dir: Path | None = None):
        self.nodes: dict[str, TreeNode] = {}  # id → node
        self.current_id: str | None = None    # current leaf node
        self.episode: int = 0
        self._save_dir = save_dir
        if save_dir:
            self._load()

    def _make_id(self, step: int) -> str:
        return f"ep{self.episode}.s{step}"

    def new_episode(self) -> None:
        """Start a new episode branch (on RESET)."""
        self.episode += 1
        self.current_id = None
        logger.info("Exploration tree: new episode %d", self.episode)

    def add_node(
        self,
        step: int,
        action: str,
        effect: str,
        state: str = "",
        next_state: str = "",
        score: int = 0,
        level: int = 1,
        player_pos: tuple[int, int] | None = None,
        world_changed: bool = False,
    ) -> TreeNode:
        """Add a new node as child of current node."""
        node_id = self._make_id(step)
        node = TreeNode(
            id=node_id,
            step=step,
            parent_id=self.current_id,
            state=state,
            action=action,
            next_state=next_state,
            effect=effect,
            score=score,
            level=level,
            player_pos=player_pos,
            world_changed=world_changed,
        )

        # Link to parent
        if self.current_id and self.current_id in self.nodes:
            self.nodes[self.current_id].children.append(node_id)

        self.nodes[node_id] = node
        self.current_id = node_id
        return node

    def attach_artifact(self, artifact_type: str, filename: str, node_id: str | None = None) -> None:
        """Attach a knowledge artifact filename to a node.

        artifact_type: 'discovery', 'hypothesis', 'summary', 'proof'
        """
        target_id = node_id or self.current_id
        if not target_id or target_id not in self.nodes:
            return

        node = self.nodes[target_id]
        bucket = {
            "discovery": node.discoveries,
            "hypothesis": node.hypotheses,
            "summary": node.summaries,
            "proof": node.proofs,
        }.get(artifact_type)

        if bucket is not None and filename not in bucket:
            bucket.append(filename)

    def get_node(self, node_id: str) -> TreeNode | None:
        return self.nodes.get(node_id)

    def get_current(self) -> TreeNode | None:
        if self.current_id:
            return self.nodes.get(self.current_id)
        return None

    def get_recent_nodes(self, n: int = 3) -> list[TreeNode]:
        """Walk backwards from current node, return last n nodes (oldest first)."""
        result = []
        nid = self.current_id
        while nid and len(result) < n:
            node = self.nodes.get(nid)
            if not node:
                break
            result.append(node)
            nid = node.parent_id
        result.reverse()
        return result

    def get_branch_path(self, node_id: str | None = None) -> list[TreeNode]:
        """Full path from root to given node (or current)."""
        target = node_id or self.current_id
        path = []
        nid = target
        while nid:
            node = self.nodes.get(nid)
            if not node:
                break
            path.append(node)
            nid = node.parent_id
        path.reverse()
        return path

    def get_subtree_str(self, node_id: str, depth: int = 3) -> str:
        """Render subtree from a node, up to `depth` levels deep."""
        node = self.nodes.get(node_id)
        if not node:
            return f"Node {node_id} not found."
        return self._render_subtree(node, depth, 0)

    def _render_subtree(self, node: TreeNode, max_depth: int, curr_depth: int) -> str:
        indent = "  " * curr_depth
        line = indent + node.compact_str()
        if curr_depth >= max_depth or not node.children:
            return line
        child_lines = []
        for cid in node.children:
            child = self.nodes.get(cid)
            if child:
                child_lines.append(self._render_subtree(child, max_depth, curr_depth + 1))
        return line + "\n" + "\n".join(child_lines)

    def search_nodes(self, query: str, max_results: int = 10) -> list[TreeNode]:
        """Search nodes by action, effect, or artifact filename."""
        q = query.lower()
        results = []
        for node in self.nodes.values():
            match = (
                q in node.action.lower()
                or q in node.effect.lower()
                or q in node.state.lower()
                or q in node.next_state.lower()
                or any(q in f.lower() for f in node.discoveries)
                or any(q in f.lower() for f in node.hypotheses)
                or any(q in f.lower() for f in node.summaries)
                or any(q in f.lower() for f in node.proofs)
            )
            if match:
                results.append(node)
                if len(results) >= max_results:
                    break
        return results

    def get_branch_summary(self, last_n: int = 20) -> str:
        """Compact summary of the current branch (last N nodes)."""
        path = self.get_branch_path()
        if not path:
            return "(no nodes yet)"
        show = path[-last_n:]
        lines = []
        for node in show:
            lines.append(node.compact_str(include_artifacts=False))
        if len(path) > last_n:
            lines.insert(0, f"... ({len(path) - last_n} earlier nodes omitted)")
        return "\n".join(lines)

    def render_recent(self, n: int = 3) -> str:
        """Render last N nodes with full detail — for default prompt injection."""
        nodes = self.get_recent_nodes(n)
        if not nodes:
            return "(no exploration history yet)"
        parts = []
        for node in nodes:
            parts.append(node.full_str())
        return "\n\n".join(parts)

    def find_world_change_nodes(self, last_n: int = 50) -> list[TreeNode]:
        """Find recent nodes where world changed — important for pattern discovery."""
        path = self.get_branch_path()
        candidates = path[-last_n:] if len(path) > last_n else path
        return [n for n in candidates if n.world_changed]

    def find_score_nodes(self) -> list[TreeNode]:
        """Find all nodes where score increased."""
        results = []
        for node in self.nodes.values():
            if "scored" in node.effect:
                results.append(node)
        return sorted(results, key=lambda n: n.step)

    def stats(self) -> str:
        """Quick stats about the tree."""
        total = len(self.nodes)
        episodes = self.episode + 1
        scored = len(self.find_score_nodes())
        world_changes = sum(1 for n in self.nodes.values() if n.world_changed)
        return (
            f"Tree: {total} nodes, {episodes} episodes, "
            f"{scored} score events, {world_changes} world changes"
        )

    # ── Persistence ──

    def save(self) -> None:
        if not self._save_dir:
            return
        self._save_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "episode": self.episode,
            "current_id": self.current_id,
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
        }
        path = self._save_dir / "exploration_tree.json"
        path.write_text(json.dumps(data, indent=1), encoding="utf-8")

    def _load(self) -> None:
        if not self._save_dir:
            return
        path = self._save_dir / "exploration_tree.json"
        if not path.is_file():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.episode = data.get("episode", 0)
            self.current_id = data.get("current_id")
            for nid, nd in data.get("nodes", {}).items():
                self.nodes[nid] = TreeNode.from_dict(nd)
            logger.info("Loaded exploration tree: %d nodes, episode %d", len(self.nodes), self.episode)
        except Exception as e:
            logger.warning("Failed to load exploration tree: %s", e)
