---
name: "Button and Gates"
description: "Game involves navigating a 5x5 block, stepping on a button to rotate a pattern until it matches a goal pattern, which unlocks the path to the goal."
---

# Game Mechanics
- We control a 5x5 player block (top 2 rows color 12, bottom 3 rows color 9). Movement is exactly 5 cells per action.
- Action 1: UP (Y -= 5)
- Action 2: DOWN (Y += 5)
- Action 3: LEFT (X -= 5)
- Action 4: RIGHT (X += 5)
- Movement is blocked if the 5x5 footprint encounters color 5 terrain.
- The timer (color 11 blocks at bottom) decreases exactly 2 cells (a 2x1 vertical sliver) every single move.
- Reaching max actions without completing the level ends the episode without advancing.

# Game Elements
- **Button / Key**: A 5x5 object (typically with colors 0, 1). Stepping on it triggers a mechanism.
- **Pattern Display**: A 6x6 symbol at the bottom-left of the screen (typically around rows 55-60, cols 3-8) made of 2x2 blocks of color 9. It represents a 3x3 grid logically. It acts as the "current state" of the gate lock.
- **Goal Symbol**: A 3x3 symbol of color 9 on the grid. This is the target pattern.
- **Goal Barrier**: A 7x7 structure of color 5 walls that surrounds the 3x3 goal area initially, preventing entry. When matched, this 7x7 barrier turns into color 0.
- **Score Indicator**: Color 8 dots at the bottom-right track the levels completed.

# Strategy & Puzzle Logic
1. Locate the Button, the Pattern Display (bottom-left), and the Goal Symbol.
2. **Initial Check**: Does the bottom-left Pattern Display ALREADY exactly match the shape of the Goal Symbol? If yes, the barrier is already open—do NOT step on the button, just path straight to the goal.
3. **Using the Rotator**: If the patterns do not match, the Button operates as a **Rotator**. Every time your 5x5 block steps ON the button (or moves around on it to toggle state), the pattern display in the bottom-left rotates 90 degrees.
4. Repeat manipulating the button to rotate the bottom-left pattern until it exactly matches the goal symbol.
5. **CRITICAL WARNING (Anti-Sphexishness)**: Do NOT accidentally step on the button again once the pattern matches! Re-triggering the button will close the barrier. Once the pattern matches, pathfind carefully AWAY from the button towards the goal. Avoid repeating cyclic action sequences that achieve nothing.
6. When the patterns match, a large-scale change will occur where the entirely 7x7 color 5 barrier surrounding the Goal will magically disappear (turning into passable terrain like color 0).
7. Pathfind your 5x5 player block to the Goal symbol now that the path is clear. Avoid color 5 obstacles. Use `run_code` pathfinding if stuck.
8. **Perfect Alignment**: Align your 5x5 block precisely over the 3x3 goal symbol. The top-left corner of your 5x5 footprint must be exactly `(Goal_Y - 1, Goal_X - 1)`. For example, if the goal's top-left is `(11, 35)`, your player's top-left must rest at `(10, 34)`.
9. Overlapping the goal exactly completes the current level, clears the board, and grants +1 score. If it's the final level, it ends with "level_up".