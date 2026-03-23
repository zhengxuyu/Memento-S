def inspect_world():
    print(f"Number of grids: {len(grids)}")
    for i, g in enumerate(grids):
        print(f"--- Grid {i} ---")
        # Find 5x5 avatar
        avatar_y, avatar_x = None, None
        for y in range(60):
            for x in range(60):
                if g[y][x] == 12 and g[y+1][x] == 12 and g[y+2][x] == 9:
                    avatar_y, avatar_x = y, x
                    break
            if avatar_y is not None: break
        print(f"Primary Avatar: {avatar_y}, {avatar_x}")
        
        # Find secondary avatar (look for color 14)
        sec_y, sec_x = None, None
        for y in range(60):
            for x in range(60):
                if g[y][x] == 14 or g[y][x+1] == 14:
                    sec_y, sec_x = y, x
                    break
            if sec_y is not None: break
        print(f"Secondary Avatar: {sec_y}, {sec_x}")
        
        # Find buttons (colors 0 and 1 in cross shape)
        for y in range(62):
            for x in range(62):
                if g[y][x+1] == 1 and g[y+1][x] == 1:
                    print(f"Button found at: {y}, {x}")
