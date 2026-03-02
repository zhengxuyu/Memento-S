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
- Movement is exactly **5 cells per action** (one full block length). The grid operates on a 5x5 step basis. Movement is blocked by color 5 terrain if there isn't a 5x5 clearance at the destination.
- The timer (color 11) ticks down every move, represented by disappearing blocks at the bottom of the screen.

# Game Elements
- **Player Block**: A 5x5 matrix at the current position.
- **Button / Key**: Objects made of color 0 and 1. Stepping on these aligns the player block and triggers large-scale terrain alterations. They can toggle gates, changing color 5 to 9, or color 9 to 5, effectively opening and closing paths.
- **Gates / Obstacles**: Color 5 acts as impassable terrain.
- **Goal**: A 3x3 footprint consisting of color 9 (which may not always form a complete solid 3x3 symbol, but clearly outlines a 3x3 area). 
- **Alignment**: To complete a level, perfectly align the **center 3x3 cells of the 5x5 player block** precisely over the 3x3 goal footprint. The top-left corner of the 5x5 block must be exactly at `(Goal_Y - 1, Goal_X - 1)`.

# Strategy
1. Locate the button (colors 0 and 1). Note its center coordinates.
2. Pathfind using a standard step-size of 5 across X and Y, making sure the entire 5x5 footprint avoids color 5 at each step.
3. Move the player block onto the button to trigger the level change.
4. Observe what was unlocked. Toggling the button opens up pathways by converting color 5 walls to other colors, and vice versa.
5. Identify the 3x3 goal (color 9). The target destination for your player block's top-left corner is `(Goal_Y - 1, Goal_X - 1)`.
6. Pathfind using steps of 5 back to the goal and overlap it precisely.
7. Minimize actions to not run out of the timer. If movement is blocked, explore alternative paths or other buttons.