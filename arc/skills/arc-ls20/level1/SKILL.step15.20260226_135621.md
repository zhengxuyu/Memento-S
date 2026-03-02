---
name: "Button and Gates"
description: "Game involves navigating a 5x5 block, stepping on a button to rotate a pattern until it matches a goal pattern, which unlocks the path to the goal."
---

# Game Mechanics
- We control a 5x5 player block (top 2 rows color 12, bottom 3 rows color 9). Movement is 1 cell per action.
- Action 1: UP (Y -= 1)
- Action 2: DOWN (Y += 1)
- Action 3: LEFT (X -= 1)
- Action 4: RIGHT (X += 1)
- Every move costs 1 action. The timer (color 11 blocks at bottom) decreases exactly 2 cells (a 2x1 vertical sliver) every move.

# Game Elements
- **Button / Key**: A small object (typically a cross shape composed of colors 0 and 1). Stepping on it with the player block triggers a mechanism.
- **Pattern Display**: A 6x6 symbol at the bottom-left of the screen (typically around rows 55-60, cols 3-8) made of 2x2 blocks of color 9. It represents a 3x3 grid logically.
- **Goal Symbol**: A 3x3 symbol of color 9 on the grid. This is the target pattern.
- **Goal Barrier**: A 7x7 structure of color 5 walls that surrounds the 3x3 goal area initially, preventing entry. When matched, this 7x7 barrier turns into empty space or opens up.

# Strategy & Puzzle Logic
1. Locate the Button, the Pattern Display (bottom-left), and the Goal Symbol.
2. Does the bottom-left Pattern Display ALREADY exactly match the shape of the Goal Symbol? If yes, path straight to the goal.
3. If patterns do not match, path to the button. The Button operates as a **Rotator**. Every time your 5x5 block moves or steps ON the button, the pattern display rotates 90 degrees clockwise.
4. Rotate until the display EXACTLY matches the goal symbol.
5. Once the pattern matches, a large-scale change will occur, deleting the 7x7 color 5 barrier around the Goal.
6. Pathfind perfectly to overlap the 3x3 goal. The player block is 5x5, with the bottom 3x5 being color 9. You need the center 3x3 of this bottom section to exactly overlap the goal's 3x3 area.
   - For a perfect overlap, the top-left corner of your 5x5 footprint must be exactly `(Goal_Y - 2, Goal_X - 1)`.
   - Example: if the goal's top-left is `(11, 35)`, your player's top-left point `(player_y, player_x)` must rest exactly at `(9, 34)`.
7. Overlapping perfectly grants +1 score, immediately triggering a level-up or granting a point. Proceed to the next level using the same rules dynamically.