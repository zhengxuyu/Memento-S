def check_3(y, x):
    if y<0 or x<0 or y>61 or x>61: return False
    for i in range(3):
        for j in range(3):
            c = grid[y+i][x+j]
            if c in [4, 5]: return False
    return True
