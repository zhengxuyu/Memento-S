---
name: spatial_reasoning
description: "Big-picture spatial reasoning about grid layout, area relationships, and game structure. Covers how to mentally divide the grid into zones, how to identify which areas are connected, and how to plan exploration order based on layout."
---

# Spatial Reasoning — Thinking About the Whole Grid

Instead of fixating on the nearest object, zoom out and think about the **overall structure** of the grid. Understanding the big picture helps you plan efficient routes and discover the game's logic.

## Dividing the Grid into Zones

Every grid can be mentally divided into distinct zones:

1. **Look at the large structures** (>100 cells) in the perception data — they form the skeleton of the layout. Walls, borders, and floor areas define the zones.
2. **Bordered rectangles** are often rooms. A rectangle of color X surrounding an area is a "room" you may need to enter.
3. **Long lines or bars** of a single color are walls or corridors. They divide the grid into separate regions.
4. **Open areas** (large contiguous floor-colored regions) are traversable zones.

## Identifying Connections Between Zones

Zones are connected by:

1. **Gaps in walls**: A 1-5 cell opening in a wall line = a doorway.
2. **Corridors**: A narrow strip of floor between two walled areas.
3. **Teleportation**: Some zones are only accessible via teleport.
4. **Triggers**: Some walls or doors only open after activating a trigger elsewhere.

**If two zones look disconnected** (no visible gap or corridor between them), look for triggers or teleporters that create the connection.

## Planning Exploration Order

Explore the grid systematically, not randomly:

1. **Start with your immediate zone**: Understand the boundaries of where you can walk freely.
2. **Find exits from your zone**: Look for gaps, corridors, or teleport points leading to other zones.
3. **Explore adjacent zones**: Move to neighboring areas through the exits you found.
4. **Leave isolated zones for later**: If a zone seems completely enclosed (bordered rectangle with no visible opening), you probably need a trigger to enter it. Come back after finding the trigger.

## Recognizing Structural Patterns

Games often have **structural clues** about the objective:

### Paired Structures
If you see two similar-looking structures (e.g., two bordered rectangles of similar size), they may be related:
- One might be a "lock" and the other a "key" (activating something in one affects the other)
- They might need to be "matched" or "aligned" through a transformation
- One might show you the target pattern and the other is the one you need to transform

### Central Objects
An object positioned at the center of the grid, or between two structures, is often a trigger or key that affects both structures.

### Enclosed Rooms with Objects Inside
If a bordered rectangle contains small objects:
- The room itself might be a puzzle
- The objects inside might be the goal (collect them all)
- You need to find the entrance — look for gaps in the border, triggers outside, or teleport points

## Using Layout to Inform Strategy

Before spending actions, ask yourself:

1. **Where is the goal likely to be?** Goals are often in bordered structures, at the edges, or in visually distinct areas.
2. **What's between me and the goal?** Walls? Corridors? Teleporters?
3. **Are there objects I haven't explored?** Check ALL four quadrants of the grid, not just the area near the player.
4. **Is there a part of the grid I've never visited?** Unexplored areas often contain the key to progress.

## When You're Stuck: The Four-Quadrant Check

If you've been going back and forth in one area without progress:

1. **Mentally divide the grid into 4 quadrants** (top-left, top-right, bottom-left, bottom-right).
2. **Which quadrants have you explored?** You probably visited 1-2 quadrants thoroughly.
3. **Go to the LEAST explored quadrant.** The solution is almost always in the part you haven't looked at.
4. **Don't just navigate there — explore it.** Walk around, try all directions, interact with objects you find.
