---
name: "Level 2 Button-Pattern Mechanics"
description: "Hypotheses about buttons, remote patterns, and scoring in level 2"
confirmed_count: 2
contradicted_count: 0
verified_at: 2026-03-20T11:21:50
---
- Buttons are marked as B (cross shapes of c11).
- We have observed the map and noticed color 0/1 spots around the button at (45,54).
- The player must reach the button, step on it, and cycle through the states of the remote area. 
- Scoring happens when the remote area's pattern perfectly matches the target pattern.
- Wasting Actions: moving into an obstacle consumes an action without moving the player.
- Confirmed blocking at row 10 beyond col 49. Had to go down to row 15.

## ✓ Evidence #1 (2026-03-20T11:21:38)
Step 195: At (10,49), moving RIGHT to (10,54) was blocked. Moved DOWN to (15,49). Confirms that obstacles exist and must be bypassed. Navigating down row 49 towards the button at 45,54.


## ✓ Evidence #2 (2026-03-20T11:21:50)
Step 200: Successfully bypassed obstacles by moving around to column 49. Reached (40,49). Confirms button is reachable by navigation sequence.
