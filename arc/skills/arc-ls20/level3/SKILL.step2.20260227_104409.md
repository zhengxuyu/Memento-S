---
name: "Level 1, 2, & 3 Game Mechanics, Pathing and Strategies"
description: "Navigating Level 3: Moving UP left corridor. Noted fog of war mechanics."
---

# Game Mechanics
- **Player Avatar / Block**: A 5x5 block (top 2 rows color 12, bottom 3 rows color 9). Movement is exactly 5x5 cells.
- **Fog of War**: Moving into unrevealed areas clears color 4 into color 3 (walkable) and structures.
- **Action Mappings**: 
  - ACTION1: Move UP (Y - 5)
  - ACTION2: Move DOWN (Y + 5)
  - ACTION3: Move LEFT (X - 5)
  - ACTION4: Move RIGHT (X + 5)
  *(Action 2/3/4 mapping to be verified, but 2=DOWN, 3=LEFT, 4=RIGHT is most consistent across past episodes).*
- **Timer & Global Limit**: Color 11 acts as a visual timer bar at the bottom.
- **Obstacles**: Moving into blocked cells (colors 4 and 5) consumes actions without changing position.
- **Objectives**: A 3x3 U-shaped goal (color 9) and a 3x3 gate-button (colors 0 and 1).

# Level 3 Details & Current Pathing
- Start position: Y=45, X=9.
- Button: Target player top-left is Y=10, X=49.
- Goal: Target player top-left is Y=50, X=54.
- **Current Strategy**:
  1. From start (45,9), move UP continuously to reach Y=5.
  2. The path will require 7 more ACTION1 calls to reach Y=5.
  3. Form Y=5, the path allows moving RIGHT along the top edge to eventually drop down to the button at (10,49).
  4. After activating the button, pathfind to the goal at (50,54).

# How To Win (Cheat Sheet)
1. Navigate via perfect 5x5-aligned routes avoiding obstacle walls (color 5).
2. Move 5x5 player block perfectly over the 3x3 button to open gate.
3. Pathfind to the goal and enclose the goal perfectly (center over color 9 U-shape).