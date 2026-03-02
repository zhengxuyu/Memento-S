def is_blocked(y, x):
    for r in range(y, y+5):
        for c in range(x, x+5):
            if grid[r][c] in [4, 5]: return True
    return False
