def find_sec(grid):
    for r in range(60):
        for c in range(60):
            # 3x3 block
            colors = set()
            is_valid = True
            for i in range(3):
                for j in range(3):
                    v = grid[r+i][c+j]
                    colors.add(v)
                    if v in [4, 5, 3, 11]: is_valid = False
            if is_valid and (0 in colors or 14 in colors or 8 in colors):
                 return r, c
    return None
