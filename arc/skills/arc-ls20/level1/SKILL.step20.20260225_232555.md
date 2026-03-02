---
name: "Button and Gates"
description: "Game involves navigating a 5x5 block, stepping on a button to rotate a pattern until it matches a goal pattern, which unlocks the path to the goal."
---

# Game Mechanics
- We control a 5x5 player block (colors 12 and 9). Movement is exactly 5 cells per action.
- Action 1: UP (Y -= 5)
- Action 2: DOWN (Y += 5)
- Action 3: LEFT (X -= 5)
- Action 4: RIGHT (X += 5)
- Movement is blocked if the 5x5 footprint encounters color 5 terrain.
- The timer (color 11 blocks at bottom) decreases every move. 

# Game Elements
- **Button / Key**: A 5x5 object (typically colors 0 and 1). Stepping on it toggles the level state.
- **Pattern Display**: A 3x3 block symbol at the bottom-left of the screen (typically around rows 55-60, cols 3-8) made of 2x2 blocks of color 9.
- **Goal Symbol**: A 3x3 symbol of color 9 on the grid. This is the target pattern.
- **Goal Barrier**: Color 5 walls surround the goal area initially.

# Strategy & Puzzle Logic
1. Locate the Button and the Goal.
2. The Button operates as a **Rotator**. Every time you step ON the button (and move OFF/ON), the pattern display in the bottom-left rotates clockwise by 90 degrees.
3. Compare the bottom-left Pattern Display to the Goal Symbol.
4. Step on the button repeatedly to rotate the bottom-left pattern until it **exactly matches** the shape of the Goal Symbol.
5. When the patterns match, the color 5 barrier surrounding the Goal will magically disappear (turn into passable color 0 or 3).
6. Pathfind your 5x5 player block to the Goal symbol.
7. Align your 5x5 block precisely over the 3x3 goal symbol. The top-left corner of your 5x5 footprint must be exactly `(Goal_Y - 1, Goal_X - 1)`. For example, if the goal's top-left is `(11, 35)`, your player's top-left must rest at `(10, 34)`.
8. Overlapping the goal exactly completes the level.