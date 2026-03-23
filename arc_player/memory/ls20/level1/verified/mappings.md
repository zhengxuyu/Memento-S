---
name: "Action mappings"
description: "Mapping of buttons"
confirmed_count: 2
contradicted_count: 2
verified_at: 2026-03-20T10:29:04
---

ACTION1 = UP
ACTION2 = DOWN
ACTION3 = LEFT
ACTION4 = RIGHT


## ✓ Evidence #1 (2026-03-20T10:26:16)
Step 72: ACTION2 moved player from (25,34) to (30,34). This confirms DOWN mapping.


## ✗ Contradiction #1 (2026-03-20T10:29:04)
Step 86: ACTION2 from (25,34) moved to (30,34) but also caused a massive remote world change (3087 cells changed), contradicting the hypothesis that movement actions only alter player position.


## ✓ Evidence #2 (2026-03-20T10:29:04)
Step 85: ACTION1 moved the player from (30,34) to (25,34), securely confirming that ACTION1 maps to moving UP.


## ✗ Contradiction #2 (2026-03-20T10:39:21)
Step 28: ACTION1 at (15,34) resulted in blocked, contradicting the hypothesis that ACTION1 always freely moves the player UP. Obstacles like the c9 lock structure at row 11 completely block upward movement.
