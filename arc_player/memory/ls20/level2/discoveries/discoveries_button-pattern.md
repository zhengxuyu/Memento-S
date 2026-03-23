---
name: "Level 2 Pattern Button"
description: "Button at (45,49) cycles a 3x3 logical pattern of c9 blocks"
confirmed_count: 0
contradicted_count: 0
---
The button at (45,49) (which is 'G' on the nav map at 40,49, wait, it's 45,49 in grid) changes a remote pattern of c9 cells in the bottom left corner (rows 55-60, cols 3-8).
This remote area consists of 3x3 logical blocks (each block is 2x2 cells).
Target shape nearby at (41,15) is a 3x3 pattern of single c9 cells:
1 1 1
1 0 0
1 0 1
We must cycle the button until the remote 3x3 pattern matches this target shape (or another target shape).
C11 shrinks by 2 cells every cycle - it acts as a timer or state indicator.