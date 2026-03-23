def check_blocked_up(grid, y, x):
    for r in range(y-5, y):
        for c in range(x, x+5):
            print(f"({r}, {c}): color {grid[r][c]}")
