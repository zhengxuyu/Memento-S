def print_patt():
    g = ""
    for r in range(11, 14):
        g += "\n"
        for c in range(35, 38):
            g += "X" if grid[r][c] == 9 else "."
    print("Goal:")
    print(g)
    
    p = ""
    for r in range(55, 61, 2):
        p += "\n"
        for c in range(3, 9, 2):
            p += "X" if grid[r][c] == 9 else "."
    print("Pattern:")
    print(p)
