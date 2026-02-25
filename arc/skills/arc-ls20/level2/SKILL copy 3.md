---
name: "Scrolling Mechanics and Level Objects - Button Alignment Challenge"
description: "Navigate a 5x5 block, trigger buttons to open gates, and perfectly center over a 3x3 goal before the timer expires."
---

# Game Mechanics
- **Player Avatar / Block**: A 5x5 block. Top 2 rows are color 12, bottom 3 rows are color 9. The center of the avatar is the exact middle pixel.
- **Movement**: The avatar moves exactly 5 cells per action (its own width and height), essentially snapping to a 5x5 grid.
  - Action 1: Move UP (Y decreases by 5 cells)
  - Action 2: Move DOWN (Y increases by 5 cells)
  - Action 3: Move LEFT (X decreases by 5 cells)
  - Action 4: Move RIGHT (X increases by 5 cells)
- **Camera/Environment Scrolling**: Moving the player near the screen boundaries can cause thousands of cells to change, indicating a scrolling grid system. Within screen boundaries, ~50 cells update.
- **Timer**: Color 11 acts as a timer at the bottom of the screen, depleting to color 3. Exactly 2 cells change per action. Fully depleting it causes "time out" and life lost. Do not waste moves!
- **Collectibles / Objects**: Color 11 can also appear as a timer and other elements.
- **Blocked Moves**: When movement is blocked by an obstacle (color 5 walls), the avatar's position does not update. The timer still updates. Reverse direction if this happens.
- **Lives**: Color 8 represents remaining lives as small 2x2 blocks at the bottom right.
- **Button / Key**: Objects made of color 0 and 1 arranged in a small complex. When the 5x5 player steps on (overlaps) these objects, they act as switches, turning impassable terrain (color 5) into passable color 0 or 3.
- **Gates / Obstacles**: Color 5 acts as impassable terrain.
- **Goal / Alignment**: A 3x3 symbol made of color 9 on the grid. To complete a level, perfectly align the **center 3x3 cells of the 5x5 player block** precisely over the 3x3 goal footprint. The boundaries of the 5x5 block will extend 1 cell past the 3x3 in all directions. Wait a few frames to register.

# Strategy & Pathing
1. Locate the button (small complex of colors 0 and 1).
2. Move the player block onto the button to unlock the path.
3. Navigate your player block efficiently towards the goal.
4. Watch out for dead ends or zigzagging paths around color 5 walls.
5. Center your 5x5 player block perfectly over the 3x3 goal to complete the level. 

# Level Specifics
## Level 1
- **Start**: Avatar center at Y=47, X=46.
- **Button**: at Y=32, X=21.
- **Goal**: at Y=12, X=36.
- **Optimal Sequence (19 moves)**:
  1-3: UP x3 (to 32,46)
  4-5: LEFT x2 (to 32,36)
  6: UP (to 27,36)
  7-9: LEFT x3 (to 27,21)
  10: DOWN (to 32,21 - triggers button)
  11: UP (to 27,21)
  12: RIGHT (to 27,26)
  13: UP (to 22,26)
  14: RIGHT (to 22,31)
  15: UP (to 17,31)
  16: RIGHT (to 17,36)
  17-19: UP x3 (aligns onto the goal and waits for register).