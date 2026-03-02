def get_all_reachable_from(sy, sx):
    q = [(sy, sx)]
    visited = set([(sy, sx)])
    r = []
    while q:
        y, x = q.pop(0)
        r.append((y, x))
        for dy, dx in [(-5,0), (5,0), (0,-5), (0,5)]:
            ny, nx = y+dy, x+dx
            if check_grid_5x5(ny, nx) and (ny, nx) not in visited:
                visited.add((ny, nx))
                q.append((ny, nx))
    return r
