def bfs_path(sy, sx, ty, tx, g):
    q = [(sy, sx, [])]
    visited = set([(sy, sx)])
    while q:
        y, x, path = q.pop(0)
        if y == ty and x == tx: return path
        for dy, dx, act in [(-5, 0, '1'), (5, 0, '2'), (0, -5, '3'), (0, 5, '4')]:
            ny, nx = y+dy, x+dx
            if is_valid_5x5(ny, nx, g) and (ny, nx) not in visited:
                visited.add((ny, nx))
                q.append((ny, nx, path+[act]))
    return None
