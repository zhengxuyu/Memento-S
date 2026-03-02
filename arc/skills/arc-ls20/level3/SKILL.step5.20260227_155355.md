---
name: "Level 1, 2, & 3 Game Mechanics, Pathing and Strategies"
description: "Found amazing discovery: 3x3 Color 11 U-shapes are TIME EXTENDERS! Picking them up adds upwards of 40 actions to the global action limit. Found multiple on Level 3."
---

# Game Mechanics
- **Player Avatar**: A 5x5 block (top 2 rows color 12, bottom 3 rows color 9). Starting position for Level 3 is (45,9).
- **Movement**: ACTION1-4 moves exactly 5 cells. Costs 1 action. (1: UP, 2: DOWN, 3: LEFT, 4: RIGHT)
- **Timer**: Color 11 bar at the bottom. Decrements 2 cells per action.
- **Button**: Centered at Y=12, X=51. Target coordinates to trigger: Player top-left at Y=10, X=49.

# Level 3 Dead Ends & Blocks
- At `(40,14)`, RIGHT is BLOCKED.
- At `(15,34)`, UP and RIGHT are BLOCKED.
- At `(20,34)`, RIGHT is BLOCKED.
- At `(25, 49)`, UP is BLOCKED! Must detour to reach `(10, 49)`.

# Current Plan
- Reached `(25,49)`. Path UP is blocked.
- Will try moving LEFT via `ACTION3` to see if there is a detour, or RIGHT.
- Once the button is pressed, the gate will open. The main goal is at Y=51, X=55 (Top left target: Y=50, X=54).

## Level 3 Cheat Sheet (from previous levels — DO NOT lose this info)
---
name: "Grid Game Winning Strategy"
description: "Press a button to open a gate, then cover the U-shaped goal to win."
---
# How To Win (step-by-step)
1. Find the 3x3 button and the 3x3 U-shaped goal on the map.
2. Navigate a path to the button.
3. Center your 5x5 player block perfectly over the 3x3 button. This opens a gate.
4. Find the newly opened path and navigate to the U-shaped goal.
5. Center your 5x5 player block perfectly over the 3x3 goal to win the level.

# Controls
- Action 1 (UP): Moves the block 5 cells up.
- Action 2 (DOWN): Moves the block 5 cells down.
- Action 3 (LEFT): Moves the block 5 cells left.
- Action 4 (RIGHT): Moves the block 5 cells right.

# Key Facts
- You control a 5x5 block; all movement is in 5-cell jumps.
- There is a strict 100-action limit for the entire episode.
- Every single move must be perfect. There is zero margin for error.
- Hitting a wall wastes an action. Plan your path carefully.
- The final goal is only accessible after covering the button.

## Evolved Skill — Level 2 (reference)
---
name: "Level 1 & 2 Game Mechanics, Pathing and Strategies"
description: "Found Level 2 layout: Navigating a 5x5 block, trigger buttons to open gates, and perfectly center over a 3x3 U-shaped goal before the timer expires."
---

# Game Mechanics
- **Player Avatar / Block**: A 5x5 block (top 2 rows color 12, bottom 3 rows color 9). Movement is exactly 5x5 cells.
- **Movement Steps**: Each movement action shifts the entire 5x5 block exactly 5 cells in the corresponding direction.
- **Timer & Global Action Limit**: The episode has a strict global limit of 100 actions. Color 11 acts as a visual timer bar at the bottom (observed at rows 61 and 62), depleting by 2 cells from the left per action.
- **Obstacles**: Moving into blocked cells (colors 4 and 5) consumes actions without changing position. 
- **Objectives**: A 3x3 U-shaped goal and a 3x3 gate-button.

# Target Coordinates for Level 2
- **Button**: 3x3 structure (colors 0 and 1) at Y=46..48, X=50..52. Target player top-left is Y=45, X=49 (centers over the button).
- **Goal**: 3x3 U-shape exactly at Y=41, X=15 (made of color 9). Target player top-left is Y=40, X=14.
- **Other Structures**: There are also 3x3 U-shapes made of color 11 at (16,15) and (51,30). These may be subsequent goals or secondary interactables.

# Current Strategy & Pathing
1. **Locate Objectives**: Identify the button and goal coordinates. For Level 2, the button is at (45, 49) and the main goal is at (40, 14).
2. **Pathfind to the Button**: Move the block through valid 5x5 squares. Navigate around the start area and align along straight corridors (e.g., X=49). Moving downwards along that corridor leads directly to the button.
3. **Activate the Button**: Position the player exactly over the button to cover it (Y=45, X=49). The surrounding gate will physically change/open. 
4. **Pathfind to the Goal**: Navigate back through the maze to the newly accessible goal. At this phase, pathfinding via strict 5x5 grid alignment is required.
5. **Enclose
... [truncated]

## Evolved Skill — Level 1 (reference)
---
name: "Button and Gates"
description: "Navigate a 5x5 player block around obstacles to step on a button, which opens the gate to the 3x3 goal, then navigate inside the open gate to perfectly enclose the goal."
---

# Game Mechanics
- Played on a 64x64 grid.
- We control a 5x5 player block (top 2 rows color 12, bottom 3 rows color 9). Movement is exactly 5 cells per action.
- Walkable area is primarily color 3 and color 0. Colors 4 and 5 are obstacles. 
- Action 1: UP (Y -= 5)
- Action 2: DOWN (Y += 5) 
- Action 3: LEFT (X -= 5)
- Action 4: RIGHT (X += 5)
- Every valid map move costs 1 action. The timer (represented by groups of color 11 blocks, typically pairs) resides at the bottom right. It decreases with every move. When the timer runs out, the episode ends (max_actions). Action 5 and 6 do nothing.

# Game Elements
- **Button / Key**: A small cross-shape object (colors 0 and 1) typically occupying a 3x3 bounding box. It sits inside a walkable 5x5 grid cell. Standing on the button (aligning the player's 5x5 square exactly over the 5x5 area containing brisket) activates it.
- **Goal Symbol**: A 3x3 symbol of color 9. It might have missing pieces, but its bounding box is 3x3. The objective is to flawlessly overlap the player's 5x5 block around this 3x3 bounding rectangle.
- **Gates & Mechanisms**: Initially, the goal is often protected by a structural gate of color 5 (or 4). Stepping on the button transforms this gate into walkable terrain (color 0 or 3), effectively "opening" the gate. In other instances, buttons toggle mechanical structures elsewhere on the grid (e.g., swapping solid segments of color 5 and 9 to open new pathways).
- **Alignment**: The player moves on a strict 5x5 grid spacing. Both the button and the goal exist centered within their respective 5x5 cells. For example, to perfectly cover a goal/button situated at (y+1, x+1)..(y+3, x+3), the player's 5x5 top-left must land at exactly (y,x). 

# Strategy
1. **Locate the Button**: Find the butt
... [truncated]