def check_btn():
    btns = []
    for y in range(60):
        for x in range(60):
            if grid[y][x] in (0,1):
                btns.append((y,x))
    print("all 0 and 1:", btns)
