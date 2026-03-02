---
name: "ARC-AGI-3 Grid Game Comprehensive Strategy"
description: "Consolidated mechanics and strategies for Levels 1-3. Key discoveries include time-extending U-shapes and a detailed pathing plan for Level 3, currently in progress."
---

# Core Game Mechanics
- **Player Avatar**: A 5x5 block (top 2 rows color 12, bottom 3 rows color 9).
- **Controls & Movement**:
    - Action 1 (UP): Moves the block 5 cells up.
    - Action 2 (DOWN): Moves the block 5 cells down.
    - Action 3 (LEFT): Moves the block 5 cells left.
    - Action 4 (RIGHT): Moves the block 5 cells right.
- **Action Limit & Timer**: There is a strict global action limit of 100 actions for the entire episode. A color 11 bar at the bottom of the screen visually represents the remaining actions, depleting by 2 cells for each action taken. Every single move must be perfect, there is zero margin for error.
- **Obstacles**: Walls (colors 4, 5) block movement. Attempting to move into a wall wastes an action, consumes a turn, and depletes the timer bar, but has no other effect on the grid.
- **Time Extenders**: 3x3 U-shapes made of color 11 are bonus items. Picking them up adds a significant number of actions (~40) to the global limit.

# How To Win (General Strategy)
1.  **Locate Objectives**: Find the 3x3 button and the 3x3 U-shaped goal on the map.
2.  **Path to Button**: Navigate a path to the button, ensuring perfect 5x5 grid alignment.
3.  **Press Button**: Center the 5x5 player block over the 3x3 button. This will open a gate, creating a new path.
4.  **Path to Goal**: Navigate through the newly opened path to the U-shaped goal.
5.  **Cover Goal**: Center the 5x5 player block over the 3x3 goal to win the level.

# Level 3 Analysis & Current Plan

## Known Coordinates & Obstacles
- **Player Start Position**: (45,9).
- **Button**: Centered in a 5x5 square. Target coordinates for player top-left: `(10, 49)`.
- **Goal**: U-shape (color 9) located at `(50, 54)`.

## Current Status & Strategy
- **Current Position**: Player top-left is at `(25, 9)`.
- **Actions Used**: 20.
- **Path Summary**: I backtracked from (20,9) to (25,9), then attempted to move LEFT from (25,9) and hit a wall.
- **Last Action**: Attempted to move LEFT from (25,9) and hit a wall.
- **Objective**: Navigate to the button at `(10, 49)`.
- **Strategy**: I have confirmed that the path to the left is a dead end. I need to continue my backtracking maneuver. The next move is to go DOWN again to get back on a main path.
