def analyze_grid():
    grid = grids[-1]
    
    # Print 5x5 avatar position
    p5_y, p5_x = None, None
    for y in range(64):
        for x in range(64):
            if grid[y][x] == 12:
                # possible 5x5 avatar top-left
                if y+4 < 64 and x+4 < 64 and grid[y+2][x] == 9:
                    # let's write a robust checker
                    pass
                    
    def find_5x5(g):
        for y in range(60):
            for x in range(60):
                if g[y][x]==12 and g[y][x+1]==12 and g[y+1][x]==12:
                    if g[y+2][x]==9 and g[y+3][x]==9 and g[y+4][x]==9:
                        return (y, x)
        return None
        
    def find_3x3(g):
        for y in range(62):
            for x in range(62):
                if g[y][x] == 9 and g[y+1][x] == 0:
                    if g[y][x+1] in [8,14]:
                        return (y, x)
        return None
        
    print(f"5x5 Avatar: {find_5x5(grid)}")
    print(f"3x3 Avatar: {find_3x3(grid)}")
