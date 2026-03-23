def check_obs(y, x):
    return [(r,c,grid[r][c]) for r in range(y, y+5) for c in range(x, x+5) if grid[r][c] in [4,5]]
