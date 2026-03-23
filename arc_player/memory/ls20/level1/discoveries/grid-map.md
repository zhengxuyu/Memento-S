---
name: "Grid Map History (step 0)"
description: "1 snapshots at Fibonacci intervals, 12x12 overview per snapshot"
confirmed_count: 0
contradicted_count: 0
---

### Step 0
      4   9  14  19  24  29  34  39  44  49  54  59 
  4   4   4   4   4   4   4   4   4   4   4   4   4 
  9   4   4   4   4   4   4   5   4   4   4   4   4 
 14   4   4   4   4   4   4   3   4   4   4   4   4 
 19   4   4   4   4   4   4   3   4   4   4   4   4 
 24   4   4   3   3   3   3   3   3   3   3   4   4 
 29   4   4   3   3   3   4   3   3   3   3   4   4 
 34   4   4   3   3   3   4   3   3   3   3   4   4 
 39   4   4   4   3   4   4   3   3   3   3   4   4 
 44   4   4   4   3   3   3   3   C   3   3   4   4 
 49   4   4   4   4   4   4   4   4   4   4   4   4 
 54   5   4   4   4   4   4   4   4   4   4   4   4 
 59   5   5   5   5   5   5   5   5   5   5   5   5 


Legend: 3=c3, 4=c4, 5=c5, C=c12

Each cell = 5x5 block | Fibonacci spacing: recent=dense, old=sparse

Player (c12) = 'C', Walls (c11) = 'B', Background varies.
Compare maps across steps to see what MOVED and what's STATIC.
