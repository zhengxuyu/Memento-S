def get_goal_area():
    print("Goal Area (52-61, 2-9):")
    for r in range(52, 62):
        print("".join(str(grid[r][c]).ljust(3) for c in range(2, 10)))
