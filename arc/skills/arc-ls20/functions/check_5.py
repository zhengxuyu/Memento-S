def check_5(y, x):
    if y<0 or x<0 or y>59 or x>59: return False
    for i in range(5):
        for j in range(5):
            c = grid[y+i][x+j]
            if c in [4, 5]: return False
    return True
