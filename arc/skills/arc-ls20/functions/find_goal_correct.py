def find_goal_correct(grid):
    # Goal is color 9, 3x3
    # Check for color 9 blocks.
    for y in range(64):
        for x in range(64):
            if grid[y][x] == 9 and grid[y][x+1] == 9 and grid[y][x+2] == 9:
                if grid[y+1][x] == 9 and grid[y+1][x+2] == 9:
                    if grid[y+2][x] == 9 and grid[y+2][x+2] == 9:
                        # Is this goal?
                        return y, x
    return None, None
