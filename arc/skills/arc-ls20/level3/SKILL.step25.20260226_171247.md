---
name: "Level 3: Multi-colored Goals, Time Pickups, and Action Economy"
description: "Core procedure to guide a 5x5 avatar through a grid maze to unlock gates via a 3x3 button, collect time pickups (color 11), and perfectly enclose a 3x3 goal."
---

# How To Win (step-by-step)

1. **Locate Objectives**: 
   - Identify the 5x5 player avatar (top 2 rows color 12, bottom 3 rows color 9).
   - Identify the **3x3 Button** (often a cross shape using colors like 0 and 1).
   - Identify the **3x3 Goal** (can be U-shaped or a distinct multicolored 3x3 block pattern).
   - Identify the **Gate** blocking the goal (same color as the timer bar, usually 11).
   - Look for **Time Pick-ups** (small structures of color 11 scattered in the maze).

2. **Collect Time Pick-ups**:
   - Stepping exactly over structures of color 11 will refill the in-game timer. The timer is visualized as a bar at the bottom of the screen (rows 61 and 62).
   - The bar depletes from left to right (e.g., losing column 18, then 19, etc.). If this bar depletes completely, the level is lost.

3. **Pathfind to Button (Extreme Efficiency Required)**: 
   - Steer your 5x5 avatar through the maze paths (color 3).
   - Strictly avoid wall cells (colors 4 and 5) — hitting them wastes an action and moves you nowhere.
   - All movements are exactly in 5x5 block increments (stride = 5).
   - **Crucial**: You have a strict global limit of 100 actions *per episode* (across all levels). You MUST pathfind optimally. Any wasted moves will result in hitting `max_actions` before clearing all levels.

4. **Trigger Button**: 
   - Align the 5x5 avatar so it perfectly envelops the 3x3 button.
   - Mathematically: Avatar top-left must be exactly at `(button_row - 1, button_col - 1)`.
   - This opens the gate.

5. **Capture Goal**: 
   - Navigate to the newly unblocked 3x3 Goal.
   - Envelop it precisely with your 5x5 avatar, exactly as you did with the button.

# Controls
- Action 1: Move UP (shifts entire 5x5 avatar 5 cells up)
- Action 2: Move DOWN (shifts entire 5x5 avatar 5 cells down)
- Action 3: Move LEFT (shifts entire 5x5 avatar 5 cells left)
- Action 4: Move RIGHT (shifts entire 5x5 avatar 5 cells right)

# Key Facts
- **Avatar Definition**: 5x5 block. Top 2 rows = color 12. Bottom 3 rows = color 9.
- **Action Economy & Timer Limit**: 
  - The bar at the bottom (color 11, rows 61-62) is the in-game timer, depleting by 1 unit per action from left to right.
  - The episode has a hard cut-off of 100 actions *total*, making completely perfect pathfinding absolutely necessary to clear all levels in a single run.
- **Grid Arithmetic**: Because objects are specifically placed and the avatar moves by 5 units, you can easily verify alignment by looking at row/column coordinates modulo 5. Perfectly centering over 3x3 items is essential.