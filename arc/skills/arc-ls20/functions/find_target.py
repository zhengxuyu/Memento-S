def find_target(grid, c):
    for y in range(len(grid)):
        for x in range(len(grid[0])):
            if grid[y][x] == c:
                return y, x
    return None
