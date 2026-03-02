def is_valid_pos(grid, r, c):
    # check 5x5 area has no 4 or 5
    if r < 0 or r > 59 or c < 0 or c > 59: return False
    for i in range(5):
        for j in range(5):
            if grid[r+i][c+j] in [4, 5]:
                return False
    return True
