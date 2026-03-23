def get_grid_walkable(grid):
    w = []
    for r in range(0, 60, 5):
        row = ""
        for c in range(0, 60, 5):
            # check what's in this 5x5 block
            colors = set()
            for y in range(r, r+5):
                for x in range(c, c+5):
                    colors.add(grid[y][x])
            if 4 in colors or 5 in colors:
                if 12 in colors and 9 in colors:
                    row += "P"
                elif 1 in colors or 0 in colors:
                    row += "B"
                else:
                    row += "X"
            else:
                if 12 in colors and 9 in colors:
                    row += "P"
                elif 8 in colors or 14 in colors:
                    row += "a"
                elif 1 in colors or 0 in colors:
                    row += "B"
                else:
                    row += "."
        w.append(row)
    return w
