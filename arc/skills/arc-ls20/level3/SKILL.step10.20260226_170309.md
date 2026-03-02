---
name: "Level 3 Grid Maze Cheat Sheet"
description: "Core procedure to navigate a 5x5 avatar, trigger button-gates, and capture U-shaped goals under strict action limits."
---

# How To Win (step-by-step)
1. **Locate Objectives**: Scan the grid to find the 3x3 Button (colors 0 and 1) and the 3x3 U-shaped Goal (color 9 or 11).
2. **Pathfind to Button**: Navigate your 5x5 avatar through the maze to the button. Avoid hitting wall cells (colors 4 and 5) to conserve your limited actions. Avatar moves exactly in 5x5 steps.
3. **Trigger Button**: Center the 5x5 avatar exactly over the 3x3 button. The top-left corner of the avatar must be perfectly 1 cell above and 1 cell left of the 3x3 button. This opens the gate blocking the goal.
4. **Pathfind to Goal**: With the gate open, navigate backward/forward through the maze to the newly accessible U-shaped goal.
5. **Capture Goal**: Enclose the 3x3 U-shaped goal by centering your 5x5 avatar perfectly over it. As with the button, the avatar's perimeter acts as an exact 1-cell border around the goal.

# Controls
- Action 1: Move UP (shifts entire 5x5 block 5 cells up)
- Action 2: Move DOWN (shifts entire 5x5 block 5 cells down)
- Action 3: Move LEFT (shifts entire 5x5 block 5 cells left)
- Action 4: Move RIGHT (shifts entire 5x5 block 5 cells right)

# Key Facts
- **Player Avatar**: You control a 5x5 block (top 2 rows color 12, bottom 3 rows color 9). Movement is strictly in 5-cell grid increments.
- **Strict Timer Limit**: There is a 100-action global limit for the entire episode (depicted by a color 11 bar at the bottom, which depletes left-to-right). Actions carry over between levels. 
- **Zero Margin for Error**: Hitting blocked cells (colors 4 and 5) costs an action without moving the avatar. Perfect, error-free pathfinding is strictly mandatory to avoid timing out.
- **Target Alignment**: All interactions (buttons, goals) require the player's 5x5 block to perfectly envelop the 3x3 target. Movement is completely grid-aligned to increments of 5, enabling modular arithmetic pathfinding.
