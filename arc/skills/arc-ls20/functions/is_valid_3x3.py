def is_valid_3x3(y, x):
    if y < 0 or y > 61 or x < 0 or x > 61: return False
    for r in range(y, y+3):
        for c in range(x, x+3):
            if grid[r][c] in [4, 5]:
                return False
    return True
