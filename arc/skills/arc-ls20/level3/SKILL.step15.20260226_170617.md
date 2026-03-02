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
   - Stepping exactly over structures of color 11 will refill the global timer (visualized as a bar at the bottom, rows 61/62). This is critical for surviving the strict 100-action limit!

3. **Pathfind to Button**: 
   - Steer your 5x5 avatar through the maze paths (color 3).
   - Strictly avoid wall cells (colors 4 and 5) — hitting them wastes an action and moves you nowhere.
   - All movements are exactly in 5x5 block increments (stride = 5).

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
- **Timer / Action Limit**: You have a global limit of 100 actions across all levels in an episode. The timer is shown as a bar (often color 11) depleting from the bottom-right towards the left. Stepping on color 11 in the maze replenishes this timer by adding cells to the left edge of the bar!
- **Grid Arithmetic**: Because objects are specifically placed and the avatar moves by 5 units, you can easily verify alignment by looking at row/column coordinates modulo 5. Perfectly centering over 3x3 items is essential.