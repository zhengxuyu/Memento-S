---
name: "Button and Gates"
description: "Game involves navigating a 5x5 player block, stepping on button-like objects to change the level layout, and perfectly aligning over a 3x3 goal."
---

# Game Mechanics
- We control a 5x5 player block consisting of two top rows of color 12 and three bottom rows of color 9.
- Action 1: UP (Y decreases by 5)
- Action 2: DOWN (Y increases by 5)
- Action 3: LEFT (X decreases by 5)
- Action 4: RIGHT (X increases by 5)
- Note: Movement is exactly **5 cells per action** (one full block length). The grid operates on a 5x5 step basis. Movement is blocked by color 5 terrain if there isn't a 5x5 clearance at the destination.

# Game Elements
- **Player Block**: A 5x5 matrix at the current position.
- **Timer**: Color 11 at the bottom. Two blocks vanish every move. Do not waste moves! If you hit an obstacle or uselessly wait, the timer still ticks down.
- **Button / Key**: Objects made of color 0 and 1 arranged in a cross-shape complex. Stepping on these aligns the player block and triggers large-scale terrain alterations (e.g., turning color 5 walls into passable color 0/3).
- **Gates / Obstacles**: Color 5 acts as impassable terrain. 
- **Goal**: A 3x3 symbol made of color 9 on the grid. 
- **Alignment**: To complete a level, perfectly align the **center 3x3 cells of the 5x5 player block** precisely over the 3x3 goal footprint. This means the boundaries of the 5x5 player block will extend exactly 1 cell past the 3x3 goal in all directions. (e.g., if goal is at `y=11, x=35`, player block's top-left must reach `y=10, x=34`).

# Strategy
1. Locate the button (colors 0 and 1). Note its center coordinates.
2. Pathfind using a standard step-size of 5 across X and Y, making sure the entire 5x5 footprint avoids color 5 at each step.
3. Move the player block onto the button to trigger the level change.
4. Observe what was unlocked.
5. Identify the 3x3 goal (color 9). The target destination for your player block's top-left corner is `(Goal_Y - 1, Goal_X - 1)`.
6. Pathfind using steps of 5 back to the goal and overlap it precisely.
7. Keep moves minimal to avoid timer running out.