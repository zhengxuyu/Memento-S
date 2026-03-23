def get_avatar(grid):
    # Primary avatar
    p1 = None
    for r in range(64):
        for c in range(64):
            if grid[r][c] == 12 and grid[r+1][c] == 12:
                # check if it's 5x5
                if grid[r+2][c] == 9:
                    p1 = (r, c)
                    break
        if p1: break
        
    p2 = None
    for r in range(64):
        for c in range(64):
            if grid[r][c] in [0,8,9,12,14]:
                # check if 3x3 block of some mixed colors
                mixed = set()
                is_3x3 = True
                for i in range(3):
                    for j in range(3):
                        if r+i>=64 or c+j>=64: is_3x3=False; break
                        v = grid[r+i][c+j]
                        if v in [4,5,3,11]:
                            is_3x3 = False; break
                        mixed.add(v)
                    if not is_3x3: break
                if is_3x3 and len(mixed) >= 3 and grid[r][c] != 0 and grid[r][c] != 1:
                    p2 = (r, c)
                    break
        if p2: break
    return p1, p2
