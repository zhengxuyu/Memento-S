def print_patch(g, sy, ey, sx, ex):
    for y in range(sy, ey):
        print(''.join(f'{g[y][x]:2}' for x in range(sx, ex)))
