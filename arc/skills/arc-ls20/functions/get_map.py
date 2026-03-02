def get_map():
    for r in range(25, 45, 5):
        s = ""
        for c in range(15, 45, 5):
            val = grid[r][c]
            if val == 3: s += "."
            elif val == 12 or val == 9: s += "P"
            elif val == 5: s += "#"
            elif val == 4: s += " "
            else: s += "?"
        print(s)
