def check_grid_area():
    print("Initial state of 55,3 to 60,8")
    for r in range(54, 61):
        row = ""
        for c in range(2, 10):
            row += f"{grid[r][c]:2d} "
        print(row)
