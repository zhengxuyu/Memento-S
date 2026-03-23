---
name: "Teleport Mechanic"
description: "Pressing the button enough times spawns an object and teleports."
confirmed_count: 2
contradicted_count: 0
verified_at: 2026-03-20T11:04:26
---

It appears that at step 43, being at the button and acting, caused the player to teleport to a completely new area `pos=(45,44)` while replacing the button with a `c0/c1` object.
I will test this assumption and explore from my new pos.

## ✓ Evidence #1 (2026-03-20T11:03:32)
Step 51-54: Moved LEFT and then UP freely from pos=(45,49). It confirmed that I am indeed fully operating in the new region starting from pos=(45,44), having teleported after interacting with the button.


## ✓ Evidence #2 (2026-03-20T11:04:26)
Step 62: Pressed UP against the c9 receptor at (11,35), caused a remote world change causing c0 cells to appear around the secondary structure (55,3)-(60,8). Confirms we are doing pattern matching/remote adjustments.
