def analyze():
    # Find player
    grid2d = grid
    py, px = None, None
    for r in range(64):
        for c in range(64):
            if grid2d[r][c] == 12:
                py, px = r, c
                break
        if py is not None:
            break
            
    # Find button
    by, bx = None, None
    b_cells = []
    for r in range(64):
        for c in range(64):
            if grid2d[r][c] in [0, 1]:
                b_cells.append((r, c))
    if b_cells:
        by = sum([r for r, c in b_cells]) // len(b_cells)
        bx = sum([c for r, c in b_cells]) // len(b_cells)
    
    # Find goal
    g_cells = []
    for r in range(30):
        for c in range(64):
            if grid2d[r][c] == 9:
                g_cells.append((r, c))
    
    # Find pattern display
    p_cells = []
    for r in range(30, 64):
        for c in range(30):
            if grid2d[r][c] == 9:
                p_cells.append((r, c))
                
    print(f"Player: {py, px}")
    print(f"Button: {by, bx} from {b_cells}")
    print(f"Goal cells: {g_cells}")
    print(f"Pattern cells: {p_cells}")
    
    # Check what the goal shape is
    if g_cells:
        min_r = min([r for r, c in g_cells])
        min_c = min([c for r, c in g_cells])
        shape = set((r - min_r, c - min_c) for r, c in g_cells)
        print("Goal shape:")
        for r in range(3):
            row = ""
            for c in range(3):
                row += "#" if (r, c) in shape else "."
            print(row)
            
    if p_cells:
        min_r = min([r for r, c in p_cells])
        min_c = min([c for r, c in p_cells])
        print("Pattern shape (blocks of 2x2):")
        for r in range(0, 6, 2):
            row = ""
            for c in range(0, 6, 2):
                if (min_r + r, min_c + c) in p_cells:
                    row += "#"
                else:
                    row += "."
            print(row)
