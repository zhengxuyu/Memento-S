def find_all_objects(grid):
    objs = {}
    for r in range(64):
        for c in range(64):
            v = grid[r][c]
            if v not in [3, 4, 11, 12, 5, 8]:
                if v not in objs:
                    objs[v] = []
                objs[v].append((r,c))
    return objs
