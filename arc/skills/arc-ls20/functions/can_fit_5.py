def can_fit_5(grid, y, x):
    if y < 0 or x < 0 or y > 59 or x > 59:
        return False
    for r in range(y, y+5):
        for c in range(x, x+5):
            if grid[r][c] == 5:
                return False
    return True
