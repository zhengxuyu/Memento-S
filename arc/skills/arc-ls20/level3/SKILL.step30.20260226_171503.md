---
name: "Level 3: Multi-colored Goals, Time Pickups, and Action Economy"
description: "Core procedure to guide a 5x5 avatar through a grid maze to unlock gates via a 3x3 button, collect time pickups (color 11), and perfectly enclose a 3x3 goal."
---

# How To Win (step-by-step)

1. **Locate Objectives**: 
   - Identify the 5x5 player avatar (top 2 rows color 12, bottom 3 rows color 9).
   - Identify the **3x3 Button** (often a cross shape using colors like 0 and 1).
   - Identify the **3x3 Goal** (can be a distinct multicolored 3x3 block pattern, e.g., colors 9, 14, 0, 8, 12).
   - Identify the **Gate** blocking the goal (same color as the timer bar, usually 11).
   - Look for **Time Pick-ups** (small structures of color 11 scattered in the maze paths).

2. **Action Economy vs. In-Game Timer**:
   - The bar at the bottom (color 11, rows 61-62) is the in-game timer. It depletes from left to right by 1 column (2 cells) per action.
   - Stepping directly on a time pickup refills this physical timer.
   - **CRITICAL WARNING**: You have a strict *global limit* of 100 actions per episode across all levels. Collecting time pickups costs valuable actions. You should ONLY collect pickups if they are on your direct optimal path, or if absolutely necessary to prevent game-over. Do not take frivolous detours.

3. **Pathfinding & Grid Arithmetic (Stride = 5)**: 
   - Steer your 5x5 avatar exactly through maze paths (color 3), avoiding walls (colors 4 and 5). 
   - Since the avatar moves in exactly 5-cell increments, its top-left coordinates `(R, C)` will always maintain the same values modulo 5 (e.g., `R % 5 == 0`, `C % 5 == 4`).
   - Perfectly enveloping an objective requires your avatar's top-left to be exactly at `(objective_row - 1, objective_col - 1)`.

4. **Trigger Button & Capture Goal (Execution)**:
   - Navigate to align the avatar perfectly over the 3x3 button area. This removes the gate.
   - Navigate to the newly unblocked 3x3 Goal and envelop it precisely. 

# Controls
- Action 1: Move UP (shifts entire 5x5 avatar 5 cells up)
- Action 2: Move DOWN (shifts entire 5x5 avatar 5 cells down)
- Action 3: Move LEFT (shifts entire 5x5 avatar 5 cells left)
- Action 4: Move RIGHT (shifts entire 5x5 avatar 5 cells right)

# Key Facts
- **Avatar Definition**: 5x5 block. Top 2 rows = color 12. Bottom 3 rows = color 9.
- **Action Economy & Timer Limit**: The episode has a hard cut-off of 100 actions *total*, making completely perfect pathfinding absolutely necessary to clear all levels in a single run.
- **Grid Alignment**: Rely on the strict 5x5 mod-grid layout to plan routes without wasting a single move. Wall collisions waste actions!
