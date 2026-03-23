    def find_5x5(g):
        for y in range(60):
            for x in range(60):
                if g[y][x]==12 and g[y][x+1]==12 and g[y+1][x]==12:
                    if g[y+2][x]==9 and g[y+3][x]==9 and g[y+4][x]==9:
                        return (y, x)
        return None
