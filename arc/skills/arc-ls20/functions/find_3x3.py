    def find_3x3(g):
        for y in range(62):
            for x in range(62):
                if g[y][x] == 9 and g[y+1][x] == 0:
                    if g[y][x+1] in [8,14]:
                        return (y, x)
        return None
