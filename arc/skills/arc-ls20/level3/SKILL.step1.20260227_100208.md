---
name: "Level 3: Multi-colored Goals, Time Pickups, and Action Economy"
description: "Core procedure to guide a 5x5 avatar through a grid maze to unlock gates via a 3x3 button, collect time pickups (color 11), and perfectly enclose a 3x3 goal."
---

# How To Win (step-by-step)

1. **Locate Objectives**: 
   - Identify the 5x5 player avatar (top 2 rows color 12, bottom 3 rows color 9).
   - Identify the **3x3 Button** (often a cross shape using colors like 0 and 1).
   - Identify the **3x3 Goal** (multicolored 3x3 block pattern, e.g., colors 9, 14, 0, 8, 12).
   - Identify the **Gate** blocking the goal (often matching the timer color 11), which disappears when the button is pressed.
   - Look for **Time Pick-ups** (3x3 hollow structures of color 11 scattered in the paths).

2. **Action Economy vs. In-Game Timer**:
   - A timer bar is located at the bottom (color 11, rows 61-62).
   - The timer depletes from left to right by 1 column (2 cells) per action.
   - Stepping squarely on a time pickup refills this physical timer.
   - **CRITICAL**: The environment enforces a hard cut-off of exactly 100 actions *per episode*. Collecting time pickups costs valuable actions. You should ONLY collect pickups if they are on your direct optimal path, or if absolutely necessary to prevent game-over from the timer running out. Avoid frivolous detours.

3. **Pathfinding & Grid Arithmetic (Stride = 5)**: 
   - Steer your 5x5 avatar exactly through maze paths (color 3), avoiding walls (colors 4 and 5). 
   - Because the avatar moves in exact 5-cell jumps, its top-left coordinates `(R, C)` will always maintain the same values modulo 5 (e.g., `R % 5 == 0, C % 5 == 4`).
   - To perfectly envelop a 3x3 objective, your avatar's 5x5 top-left `(R, C)` must be placed exactly at `(objective_row - 1, objective_col - 1)`.

4. **Trigger Button & Capture Goal (Execution)**:
   - Calculate the precise path to the 3x3 Button.
   - Align the avatar precisely over the button to suppress the gate.
   - Calculate the precise path to the 3x3 Goal and envelop it to clear the level. Look out for action economy - every step counts.

# Controls
- Action 1: Move UP (shifts entire 5x5 avatar 5 cells up)
- Action 2: Move DOWN (shifts entire 5x5 avatar 5 cells down)
- Action 3: Move LEFT (shifts entire 5x5 avatar 5 cells left)
- Action 4: Move RIGHT (shifts entire 5x5 avatar 5 cells right)

# Key Facts
- **Avatar Definition**: 5x5 block. Top 2 rows = color 12. Bottom 3 rows = color 9.
- **Action Economy Limit**: 100 Actions max per episode. Standard movements and pathfinding consume the vast majority of these actions. Completely perfect, no-bumping pathfinding is essential to clear levels within the 100-action limit. Wall collisions waste steps and guarantee failure!
- **Time Pickups**: Identifying 3x3 hollow structures of color 11. Envelope these to refill the timer if needed.
- **Grid Alignment**: Rely strictly on the 5x5 mod-grid layout to plan routes step-by-step. Verify your path respects the mod-grid to guarantee you perfectly envelope objectives and never snag on structural corners.
