def get_neighbors(y, x, g):
    res = []
    if check_5x5(y-5, x, g): res.append((y-5, x, 'UP(1)'))
    if check_5x5(y+5, x, g): res.append((y+5, x, 'DOWN(2)'))
    if check_5x5(y, x-5, g): res.append((y, x-5, 'LEFT(3)'))
    if check_5x5(y, x+5, g): res.append((y, x+5, 'RIGHT(4)'))
    return res
