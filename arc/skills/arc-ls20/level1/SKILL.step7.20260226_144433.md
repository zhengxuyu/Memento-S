---
name: "Button and Gates"
description: "Navigate a 5x5 block around obstacles (colors 4 and 5) to hit a button (colors 0 and 1) that unlocks the path to a 3x3 goal (color 9)."
---

# Game Mechanics
- We control a 5x5 player block (top 2 rows color 12, bottom 3 rows color 9). Movement is 5 cells per action.
- Walkable area is color 3. Colors 4 and 5 are obstacles. 
- Action 1: UP (Y -= 5)
- Action 2: DOWN (Y += 5) 
- Action 3: LEFT (X -= 5)
- Action 4: RIGHT (X += 5)
- Every move costs 1 action. The timer (color 11 blocks at bottom) decreases by 1 column (2 cells) every move. When the timer runs out, the episode ends.

# Game Elements
- **Button / Key**: A small cross-shape object (colors 0 and 1). Overlapping it with the player block rotates the Pattern Display 90 degrees clockwise.
- **Pattern Display**: A 6x6 symbol at the bottom-left made of 2x2 blocks of color 9. It logically represents a 3x3 grid.
- **Goal Symbol**: A 3x3 symbol of color 9 on the grid. This is the target pattern.
- **Obstacles**: Color 5 and color 4 are barriers.

# Strategy
1. Locate the Button (colors 0,1), Pattern Display (bottom-left), and Goal Symbol (3x3 color 9).
2. Compare the Display to the Goal. If they don't exactly match, navigate around obstacles (colors 4,5) to the Button. 
3. Note: The path to the button may not be a straight line. Colors 4 and 5 will restrict movement, requiring a zig-zag approach. Keep the 5x5 bounds bounds of the player block strictly on walkable colors 3, 0, or 1.
4. Step on the button (e.g., move back and forth Left/Right) to rotate the display until it precisely matches the goal exactly.
5. Pathfind to the goal, aligning perfectly so the 5x5 block completely encloses the 3x3 goal.