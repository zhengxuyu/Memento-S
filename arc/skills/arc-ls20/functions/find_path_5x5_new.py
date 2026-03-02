def find_path_5x5_new(sy, sx, ty, tx):
    from collections import deque
    q = deque([(sy, sx, [])])
    visited = {(sy, sx)}
    while q:
        y, x, path = q.popleft()
        if (y, x) == (ty, tx): return path
        for dy, dx, a in [(-5,0,1), (5,0,2), (0,-5,3), (0,5,4)]:
            ny, nx = y+dy, x+dx
            if 0<=ny<=59 and 0<=nx<=59 and not is_blocked(ny, nx):
                if (ny, nx) not in visited:
                    visited.add((ny, nx))
                    q.append((ny, nx, path+[a]))
    return None
