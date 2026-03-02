def show_walkable():
    for y in range(0, 60, 5):
        row = ""
        for x in range(4, 60, 5):
            valid = True
            for i in range(5):
                for j in range(5):
                    if y+i<60 and x+j<60:
                        if grid[y+i][x+j] in (4, 5):
                            valid = False
            if y == 25 and x == 19:
                row += "P"
            elif y == 10 and x == 34:
                row += "G"
            else:
                row += "." if valid else "X"
        print(row)
