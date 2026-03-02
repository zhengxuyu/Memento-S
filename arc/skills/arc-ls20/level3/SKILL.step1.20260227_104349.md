---
name: "Level 1, 2, & 3 Game Mechanics, Pathing and Strategies"
description: "Found Level 3 layout: Button at (10,49), Goal at (50,54). Positioned at (5,19) in the upper corridor moving towards the button."
---

# Game Mechanics
- **Player Avatar / Block**: A 5x5 block (top 2 rows color 12, bottom 3 rows color 9). Movement is exactly 5x5 cells.
- **Action Mappings**: 
  - ACTION1: Move UP (Y - 5)
  - ACTION2: Move RIGHT (X + 5)
  - ACTION3: Move DOWN (Y + 5)
  - ACTION4: Move LEFT (X - 5)
- **Timer & Global Action Limit**: The episode has a strict global limit. Color 11 acts as a visual timer bar at the bottom, depleting by 2 cells from the left per action.
- **Obstacles**: Moving into blocked cells (colors 4 and 5) consumes actions without changing position. Avoid unnecessary bumps.
- **Objectives**: A 3x3 U-shaped goal (color 9) and a 3x3 gate-button (colors 0 and 1). Sometimes time pickups (3x3 hollow structures of color 11) are scattered around the map to restore time.

# Coordinates for Levels

**Level 2**
- Button: Target player top-left is Y=45, X=49 (centers over the button).
- Goal: Target player top-left is Y=40, X=14.
*(Successfully completed in 38 actions!)*

**Level 3**
- Start position: Y=45, X=9.
- Button: 3x3 structure at Y=11..13, X=50..52. Target player top-left is Y=10, X=49.
- Goal: exactly at Y=51..53, X=55..57. Target player top-left is Y=50, X=54.

# Current Strategy & Pathing
1. **Locate Objectives**: Identified the button at target (10, 49) and main goal at (50, 54).
2. **Explore carefully (Level 3)**: Starting at (45,9), navigated the left corridor UP, reaching Y=5. The path allows moving RIGHT along the top edge. Currently at (5,19), moving RIGHT to eventually drop down to the button at (10,49).
3. **Activate the Button**: Position the player exactly over the button to cover it. The surrounding gate will physically change/open. 
4. **Pathfind to the Goal**: Navigate through the maze to the newly accessible goal at Y=50, X=54. Enclose perfectly.