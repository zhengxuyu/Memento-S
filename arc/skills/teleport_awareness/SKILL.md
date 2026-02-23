---
name: teleport_awareness
description: "Understanding and exploiting teleportation mechanics in grid games. Covers how to detect teleportation, map teleport destinations, use teleports as navigation tools, and explore the areas accessible from teleport endpoints."
---

# Teleport Awareness — Using Portals as Navigation Tools

Some grid games feature **teleportation** — your player jumps to a distant location when stepping on a specific cell or crossing a boundary. This is NOT a bug or a wall — it's a **game mechanic** you should exploit.

## Detecting Teleportation

Teleportation has happened when:

1. **navigate_to reports "TELEPORTATION"**: The log shows a large position delta (e.g., `(33, 26) -> (57, 5)` with delta=24,21).
2. **Player position jumps**: Your position changes by much more than 5 cells in a single action.
3. **Completely different surroundings**: After one action, you see entirely different objects and walls around you.

## Mapping Teleport Links

Teleports usually work as **bidirectional portals** or **one-way warps**. When you discover one:

1. **Record the entry point**: The exact position and direction that triggered the teleport.
2. **Record the destination**: Where you ended up.
3. **Test the reverse**: Try to teleport back. If you can, it's a two-way portal.
4. **Test all directions**: Some portals only activate from a specific direction. Try all 4 from the entry point.

Use `update_game_notes` to record: "Teleport: (33,26) going LEFT → (57,5)" so you remember on retries.

## Teleport Destinations Are Important Areas

**CRITICAL INSIGHT**: The game doesn't teleport you to random locations. Teleport destinations are almost always **important areas** that you need to explore:

1. **After teleporting**, STOP trying to get back. Instead, **explore the destination area**.
2. The destination may contain:
   - A trigger or switch you need to activate
   - Collectible items required before the goal opens
   - A different entrance to an area you couldn't reach directly
   - A puzzle room with its own mechanics
3. **Spend at least 3-5 actions** exploring the teleport destination before trying to leave.

## Using Teleports Strategically

Once you've mapped the teleport network:

1. **Use teleports as shortcuts**: If the direct path is blocked, the teleport might take you to the other side of the obstacle.
2. **Try to reach areas near the teleport destination by walking from there**: The destination is your new starting point. Explore outward from it.
3. **Some puzzles require teleporting back and forth**: You may need to activate something at location A (via teleport), then return to location B (via reverse teleport) to use the result.

## When You Keep Getting Teleported Away

If you're trying to reach a target but keep getting teleported away:

1. **The area you're trying to reach might be deliberately blocked.** The teleport IS the game telling you "go here instead."
2. **Explore the teleport destination FIRST.** There may be a switch or trigger there that removes the teleport or opens a direct path.
3. **Approach from a different direction.** Teleports are often directional — you might be able to reach the same area from a different angle without hitting the portal.
4. **The teleport might be the intended mechanic.** Maybe the game wants you to USE the teleport to access the goal, not to avoid it.

## Teleport + Trigger Combos

A common game pattern:

1. You start in area A. A goal/door is visible but unreachable.
2. Moving in certain directions teleports you to area B (a separate room).
3. Area B contains a trigger (cross/switch).
4. Activating the trigger in area B transforms the grid in area A (rotates the door pattern, opens a wall).
5. Teleporting back to area A, the path is now open.

**When you see this pattern**: Don't fight the teleport. Go to area B, find the trigger, activate it, then return to area A.
