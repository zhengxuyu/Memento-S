def can_fit_5x5(grid, y, x):
    if y < 0 or x < 0 or y+5 > 64 or x+5 > 64: return False
    for i in range(5):
        for j in range(5):
            if grid[y+i][x+j] in (4, 5): return False
    return True
