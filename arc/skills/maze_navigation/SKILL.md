---
name: maze_navigation
description: "Strategies for navigating through walled structures, corridors, and maze-like environments where direct paths are blocked. Covers wall-following, corridor tracing, indirect routing, and recognizing when you're trapped in a bounded area."
---

# Maze Navigation — Getting Through Walled Structures

When `navigate_to` keeps hitting walls or you keep ending up at the same position, you are likely inside a **maze or walled corridor**. Direct BFS paths fail because they assume open space. You need maze-specific strategies.

## Recognizing You're in a Maze

Signs that you're dealing with a maze structure:

1. **Repeated wall hits**: 3+ consecutive `navigate_to` calls to the same target fail with walls recorded.
2. **Player stays at same position**: The navigator reports "player didn't move" or "recorded wall".
3. **Limited movement**: You can move in some directions but not others from the same position.
4. **Narrow corridors**: The perception shows walls on both sides of your position, leaving only 1-2 open directions.

When you recognize these signs, **STOP calling navigate_to to the same target**. The path is blocked — you need to find the actual route through the maze.

## Wall-Following Strategy

When stuck behind walls, follow the wall to find an opening:

1. **Pick a wall side** (left or right — stay consistent).
2. **Move along the wall**: If blocked going LEFT, try UP or DOWN to slide along the wall edge.
3. **Check for openings**: After each step, try the blocked direction again. If it works, the wall has an opening there.
4. **Mark dead ends**: If you reach a position where 3 directions are blocked, reverse — it's a dead end.

Concretely:
- If `navigate_to(target)` hits a wall at position (R,C) going LEFT, try navigating to (R-5, C) or (R+5, C) to move along the wall.
- After moving along, try `navigate_to(target)` again from the new position.
- Repeat: move along wall, try target, move along, try target.

## Corridor Tracing

Many grids have **corridors** — narrow paths between walls. To navigate corridors:

1. **Identify your corridor**: Look at your position and which directions are walkable vs blocked.
2. **Follow the corridor**: Move in the open direction(s). Don't try to cut through walls.
3. **At junctions** (2+ open directions): Choose the direction that brings you **closer to your target** in terms of row/column.
4. **Don't backtrack**: Mark positions you've already visited. If you arrive at a visited position, take a different branch.

## Indirect Routing

Sometimes the only path to a target goes AWAY from it first:

1. **If blocked in the direct direction**: Try going perpendicular (e.g., if blocked going left, try up or down first).
2. **If blocked in ALL directions**: You're in a dead end or enclosed area. Look for:
   - A corridor exit you missed
   - A trigger or switch nearby that might open a wall
   - A teleportation point (see teleport_awareness skill)
3. **Try the opposite direction**: Some mazes require going far away from the target first, then approaching from a different side.

## Bounded Area Detection

If you keep bouncing between the same 3-5 positions:

1. **You're trapped in a small room or corridor loop.**
2. **Map your boundary**: Try all 4 directions from each position to find every wall.
3. **Look for exits you missed**: Small openings (1 cell wide) are easy to miss at 5-cell step size.
4. **Look for interactive objects inside the room**: There may be a switch or trigger INSIDE the bounded area that opens an exit.
5. **Consider that the room itself might be the puzzle**: Maybe you need to do something specific inside this area (step on a pattern, activate a sequence) before a wall opens.

## When navigate_to Keeps Failing

If you've called `navigate_to` to the same target 3+ times and it keeps failing:

1. **DO NOT call it a 4th time.** The direct path is blocked.
2. **Try an intermediate waypoint**: Navigate to a position you CAN reach that's in a different area, then try the target from there.
3. **Explore systematically**: Move to unvisited areas of the grid. The path to your target may require going through a section you haven't explored yet.
4. **Use single actions**: Sometimes manual ACTION1-4 from a specific position succeeds where BFS fails, because the step lands you at a corridor opening.
