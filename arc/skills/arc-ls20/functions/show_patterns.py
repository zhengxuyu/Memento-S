def show_patterns():
    print("Goal pattern:")
    for y in range(10, 15):
        print(" ".join(str(grid[y][x]).rjust(2) for x in range(34, 39)))
    print("Bottom-left pattern:")
    for y in range(55, 61):
        print(" ".join(str(grid[y][x]).rjust(2) for x in range(3, 9)))
