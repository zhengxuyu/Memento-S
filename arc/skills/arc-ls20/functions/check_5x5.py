def check_5x5(y,x):
    for r in range(y,y+5):
        for c in range(x,x+5):
            if grid[r][c] in [4,5]: return False
    return True
