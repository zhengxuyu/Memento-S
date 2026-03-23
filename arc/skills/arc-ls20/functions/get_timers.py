def get_timers(grid):
    timers = []
    for r in range(64):
        for c in range(64):
            if grid[r][c] == 11:
                # check if it's top-left of 3x3
                is_timer = True
                for i in range(3):
                    for j in range(3):
                        if r+i>=64 or c+j>=64: is_timer = False; break
                        if not (i==1 and j==1):
                            if grid[r+i][c+j] != 11: is_timer = False
                if is_timer:
                    timers.append((r,c))
    return timers
