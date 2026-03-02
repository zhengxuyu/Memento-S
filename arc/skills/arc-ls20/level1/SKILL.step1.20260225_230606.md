---
name: "Button and Gates"
description: "Game involves navigating a 5x5 block, stepping on button-like objects to change the level layout, and perfectly aligning over a 3x3 goal."
---

# Game Mechanics
- We control a 5x5 block consisting of two top rows of color 12 and three bottom rows of color 9.
- Action 1: UP (Y decreases by 5)
- Action 2: DOWN (Y increases by 5)
- Action 3: LEFT (X decreases by 5)
- Action 4: RIGHT (X increases by 5)

# Game Elements
- **Player Block**: A 5x5 matrix at the current position.
- **Timer**: Color 11 at the bottom. Two blocks vanish every move. Do not waste moves!
- **Button / Key**: Objects made of color 0 and 1 arranged in a small complex. When the player steps on (overlaps) these objects, they act as switches, unlocking pathways.
- **Gates / Obstacles**: Color 5 acts as impassable terrain. Stepping on the button "unlocks" areas of color 5 near the goal by turning them into passable color 0 or 3.
- **Goal**: A 3x3 symbol made of color 9 on the grid. 
- **Alignment**: To complete a level, perfectly align the **center 3x3 cells of the 5x5 player block** precisely over the 3x3 goal footprint. This means the boundaries of the 5x5 block will extend 1 cell past the 3x3 in all directions.

# Strategy
1. The shortest path to the button is 1, 1, 1, 3, 3, 3, 3.
2. Locate the button (small complex of colors 0 and 1).
3. Move the player block onto the button to trigger a level change.
4. Observe what was unlocked (usually a region of impassable color 5 around the color 9 goal symbol).
5. Navigate to the goal.
6. Perfectly align the 5x5 player block so it covers the 3x3 goal completely (the centers must match).
7. The level will reset and progress will continue. Keep moving!