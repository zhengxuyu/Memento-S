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
- Every move costs 1 action. The timer (color 11 blocks) decreases as moves are made. When the timer runs out, the episode ends (max_actions). Action 5 and 6 do nothing.

# Game Elements
- **Button / Key**: A small cross-shape object (colors 0 and 1) typically occupying a 3x3 bounding box. It sits inside a 5x5 grid cell. Standing on the button (aligning the player's 5x5 square exactly over the 5x5 area containing the button) activates it.
- **Goal Symbol**: A 3x3 symbol of color 9. It might have missing pieces, but its bounding box is 3x3. The objective is to flawlessly overlap the player's 5x5 block around this 3x3 bounding rectangle.
- **Gates**: Initially, the goal is protected by a structural gate of color 5 (or 4). Stepping on the button transforms this gate into walkable terrain (color 0 or 3), effectively "opening" the gate.
- **Alignment**: The player moves on a strict 5x5 grid spacing. Both the button and the goal exist centered within their respective 5x5 cells. For example, to perfectly cover a goal/button situated at (y+1, x+1)..(y+3, x+3), the player's 5x5 top-left must land at exactly (y,x). 

# Strategy
1. **Locate the Button**: Find the button (e.g., color 0 or 1 cross). 
2. **Find Path to Button**: Traverse strictly on walkable terrain (color 3) dodging obstacles (colors 4 and 5) in multiples of 5x5.
3. **Open the Gate**: Move the player block completely ONTO the button to align their centers.
4. **Find Path to Goal**: Once the barrier is removed, move OFF the button and toward the open gate. Find the path strictly in 5x5 increments.
5. **Enclose perfectly**: The player's bounding block must overlap the goal coordinates precisely (i.e. if goal bounding box is 11-13y, 35-37x, player top-left must be at 10y, 34x) to trigger the level_up sequence and secure the score.