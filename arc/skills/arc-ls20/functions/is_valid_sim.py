def is_valid_sim(grid, py, px):
    for r in range(py, py+5):
        for c in range(px, px+5):
            if grid[r][c] in [4, 5]: return False
    return True
