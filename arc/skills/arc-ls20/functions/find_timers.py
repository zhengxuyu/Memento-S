def find_timers(g):
    timers = []
    for r in range(60):
        for c in range(60):
            if g[r][c] == 11 and g[r+2][c] == 11 and g[r][c+2] == 11 and g[r+2][c+2] == 11:
                # possible 3x3 hollow
                if g[r+1][c+1] != 11:
                    timers.append((r, c))
    return timers
