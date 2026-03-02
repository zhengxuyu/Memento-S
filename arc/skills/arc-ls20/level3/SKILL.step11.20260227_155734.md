---
name: "ARC-AGI-3 Grid Game Comprehensive Strategy"
description: "Consolidated mechanics and strategies for Levels 1-3. Key discoveries include time-extending U-shapes and a detailed pathing plan for Level 3, currently in progress."
---

# Core Game Mechanics
- **Player Avatar**: A 5x5 block (top 2 rows color 12, bottom 3 rows color 9).
- **Movement**: Actions 1-4 move the avatar exactly 5 cells (UP, DOWN, LEFT, RIGHT). Each move costs 1 action.
- **Action Limit & Timer**: There is a strict global action limit (around 100). A color 11 bar at the bottom of the screen visually represents the remaining actions, depleting by 2 cells for each action taken.
- **Obstacles**: Walls (colors 4, 5) block movement. Attempting to move into a wall wastes an action.
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
- **Known Blocks / Dead Ends**:
    - At `(40,14)`, RIGHT is BLOCKED.
    - At `(35,9)`, RIGHT is BLOCKED.
    - At `(15,34)`, UP and RIGHT are BLOCKED.
    - At `(20,34)`, RIGHT is BLOCKED.
    - At `(25, 49)`, UP is BLOCKED. This is a critical obstacle en route to the button.

## Current Status & Strategy
- **Current Position**: Player top-left is at `(25, 9)`.
- **Actions Used**: 10.
- **Objective**: Navigate to the button at `(10, 49)`.
- **Recent History**: Started at `(45,9)`. Moved up and found rightward paths blocked at `(40,14)` and `(35,9)`. The current position `(25,9)` was reached by continuing to explore upwards to find a clear path to the east.
- **Strategy**: The immediate priority is to move RIGHT from `(25, 9)` to get closer to the button's X-coordinate of 49. Given the known block preventing an UPWARD move at `(25, 49)`, the path will likely require moving right as far as possible, then moving UP again to circumvent that specific obstacle, before finally aligning with the button at `(10, 49)`. Exploration must remain cautious to avoid wasting actions.
