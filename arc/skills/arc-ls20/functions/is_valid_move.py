def is_valid_move(grid, y, x):
    # check 5x5 block around (y,x)
    for ry in range(5):
        for rx in range(5):
            cy, cx = y + ry, x + rx
            if cy < 0 or cx < 0 or cy >= len(grid) or cx >= len(grid[0]):
                return False
            if grid[cy][cx] in (4, 5):
                return False
    return True
