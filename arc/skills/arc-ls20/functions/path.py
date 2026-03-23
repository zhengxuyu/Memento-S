def path():
    # just print where the button is and what surrounds it
    for r in range(8, 18):
        row_str = ""
        for c in range(45, 60):
            val = grid[r][c]
            if val == 4 or val == 5:
                row_str += "#"
            elif val == 3:
                row_str += "."
            else:
                row_str += str(val)
        print(row_str)
