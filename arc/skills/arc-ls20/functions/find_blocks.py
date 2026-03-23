def find_blocks(g):
    for y in range(60):
        for x in range(60):
            if g[y][x] == 12 and g[y+1][x] == 12 and g[y+2][x] == 9:
                print(f"5x5 avatar at {y}, {x}")
            if g[y][x] == 9 and g[y+1][x] == 0 and g[y+2][x] == 12:
                print(f"3x3 maybe at {y},{x}? color {g[y][x]}")
