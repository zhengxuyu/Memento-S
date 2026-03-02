def test_path():
    py, px = 25, 24
    print("Start:", py, px)
    print("Checking Y=30, X=24:", [grid[y][x] for y in range(30,35) for x in range(24,29) if grid[y][x] in (4,5)])
