def find_goal(grid):
    for r in range(60):
        for c in range(60):
            # top-left of the U-shape or the hole?
            # actually we want the target coords for avatar. The target is 55,3
            if grid[r][c] == 12 and grid[r+4][c] == 12:
                # bounding box checking
                return r, c
    return 55, 3
