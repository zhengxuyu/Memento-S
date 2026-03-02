def explore_target_area():
    print("Map 5..20 x 30..45:")
    res = []
    for y in range(5, 20):
        row = []
        for x in range(30, 45):
            row.append(str(grid[y][x]).rjust(2))
        res.append(" ".join(row))
    print("\n".join(res))
