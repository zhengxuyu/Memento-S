def print_path():
    grid = grids[-1]
    sy, sx = 25, 44
    for r in range(25, 30):
        s = ""
        for c in range(44, 59):
            s += str(grid[r][c]).ljust(3)
        print(s)
