---
name: "Pattern Match Scoring"
description: "Scoring occurs when the bottom-left c9 pattern matches the top-right c9 pattern"
confirmed_count: 0
contradicted_count: 2
disproved_at: 2026-03-20T10:40:17
---

My hypothesis is that the goal of this level is to make the 3x3 grid of 2x2 c9 blocks at the bottom-left (55,3)-(60,8) geometrically match the shape of the 3x3 grid of 1x1 c9 blocks at the top-right (11,35)-(13,37).

Top right pattern (1x1 blocks):
```
1 1 1
0 0 1
1 1 1
```

Current bottom left pattern (2x2 blocks):
```
1 0 1
1 0 0
1 1 1
```

By standing on the button at (30,19), different actions might shift these blocks. Let's test which actions move which blocks in which direction.


## ✗ Contradiction #1 (2026-03-20T10:39:01)
Step 17: ACTION3 at player (30,19) moving to (30,14). Expected the remote pattern to stay modified or change in place, but it didn't change at all upon moving away. No remote change occurred. Moving off the button only toggles changes in certain directions.


## ✗ Contradiction #2 (2026-03-20T10:40:17)
Step 44: The game does not score by matching a remote pattern on a button press at c0 (31,21) and c1 (32,20). The world change away from the player at (40,39) was in fact a complete resetting of the entire board after I encountered a game over state by crashing into c3 (Snake tail) at (25,34). Pattern matching is unlikely the primary mechanism.
