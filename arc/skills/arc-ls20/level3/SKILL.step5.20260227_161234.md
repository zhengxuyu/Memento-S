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

## Current Status & Strategy
- **Current Position**: Player top-left is at `(35, 9)`.
- **Actions Used**: 4.
- **Objective**: Navigate to the button at `(10, 49)`.
- **Strategy**: I have moved UP and DOWN and am now at (35,9). My Y position is incorrect for the button, and I need to start moving right. I'll begin by moving RIGHT, and then re-evaluate my path to get to (10, 49).

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
5. Center your 5x5 player block perfectly over the 3x3 goal to win the- level.

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
