def check_blocked_left(y, x):
    grid = grids[-1]
    for r in range(y, y+5):
        print(f"Cell ({r}, {x-1}) is {grid[r][x-1]}")
