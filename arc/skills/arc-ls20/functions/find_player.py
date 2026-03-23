def find_player(grid):
    for r in range(60):
        for c in range(60):
            if grid[r][c] == 12 and grid[r+1][c] == 12 and grid[r+2][c] == 9:
                return r, c
    return None
