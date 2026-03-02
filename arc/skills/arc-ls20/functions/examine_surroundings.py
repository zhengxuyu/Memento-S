def examine_surroundings(y, x, grid=grids[-1]):
    for r in range(y-1, y+6):
        row = ""
        for c in range(x-1, x+6):
            if r >= 0 and r < 64 and c >= 0 and c < 64:
                row += str(grid[r][c]).rjust(2) + " "
        print(row)
