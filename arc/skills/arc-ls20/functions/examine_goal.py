def examine_goal():
    print("Goal area pattern (y=10..14, x=34..38):")
    for y in range(10, 15):
        print(" ".join(str(grid[y][x]).rjust(2) for x in range(34, 39)))
