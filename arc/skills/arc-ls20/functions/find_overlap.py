def find_overlap(sy, sx, ty, tx):
    from collections import deque
    q = deque([(sy, sx, [])])
    visited = set([(sy, sx)])
    # allow overlap with color 5 for the bottom 3x5 player part?
    # let's find out exactly what part of player can overlap 5
    # or maybe top 2 rows?
    # what if we just print the barrier around the goal in all past grids?
    barriers = []
    for g in grids:
        b = []
        for r in range(9, 16):
            row = []
            for c in range(33, 40):
                row.append(g[r][c])
            b.append(row)
        if not barriers or b != barriers[-1]:
            barriers.append(b)
    for i, b in enumerate(barriers[-4:]):
         print(f"Barrier shape {i}:")
         for row in b: print(" ".join(map(str, row)))
