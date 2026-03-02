---
name: "Button and Gates"
description: "Navigate a 5x5 player block around obstacles to step on a button, which opens the gate to the 3x3 goal, then navigate inside the open gate to perfectly enclose the goal."
---

# Game Mechanics
- We control a 5x5 player block (top 2 rows color 12, bottom 3 rows color 9). Movement is exactly 5 cells per action.
- Walkable area is primarily color 3. Colors 4 and 5 are obstacles. 
- Action 1: UP (Y -= 5)
- Action 2: DOWN (Y += 5) 
- Action 3: LEFT (X -= 5)
- Action 4: RIGHT (X += 5)
- Every move costs 1 action. The timer (color 11 blocks at bottom) decreases as moves are made. When the timer runs out, the episode ends (max_actions).

# Game Elements
- **Button / Key**: A small cross-shape object (colors 0 and 1) situated on the 5x5 grid. Overlapping the player block perfectly over it activates it.
- **Goal Symbol**: A 3x3 symbol of color 9. The objective is to flawlessly overlap the player's 5x5 block such that it visually centers around and effectively encloses this 3x3 goal.
- **Gates**: Initially, the goal is protected by a structural gate of color 5 (or 4). This acts as an impenetrable barrier. Stepping on the button transforms this gate into walkable color 0, effectively "opening" the gate.
- **Alignment**: The player's center, the button's center, and the goal's center all operate on a strict 5x5 spatial grid offset. 

# Strategy
1. **Locate the Button**: Find the button (e.g., color 0 or 1 cross). 
2. **Find Path to Button**: Traverse strictly on walkable terrain (color 3) dodging obstacles (colors 4 and 5). Movement must be aligned to the 5x5 grid spacing steps.
3. **Open the Gate**: Move the player block over the button to align their centers. The surrounding gate will disappear (turning into walkable space).
4. **Find Path to Goal**: Once the barrier is removed, immediately pathfind to the newly accessible goal.
5. **Enclose perfectly**: The player's bounding block must perfectly overlap the goal coordinates to trigger the level_up sequence and secure the score.