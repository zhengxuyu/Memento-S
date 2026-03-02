def check_valid(grid, py, px):
    for y in range(py, py+5):
        for x in range(px, px+5):
            if y < 0 or y >= 64 or x < 0 or x >= 64:
                return False
            # Can walk on 3, 0, 1
            if grid[y][x] not in [3, 0, 1]:
                return False
    return True
