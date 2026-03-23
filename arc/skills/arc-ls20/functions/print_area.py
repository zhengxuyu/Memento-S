def print_area(grid, sy, ey, sx, ex):
    for y in range(sy, ey):
        row = []
        for x in range(sx, ex):
            row.append(f"{grid[y][x]:2d}")
        print(" ".join(row))
