def get_path_real_current(sy, sx, ty, tx):
    from collections import deque
    q = deque([(sy, sx, [])])
    visited = {(sy, sx)}
    while q:
        y, x, path = q.popleft()
        if (y, x) == (ty, tx): return path
        for dy, dx, action in [(-5,0,1), (5,0,2), (0,-5,3), (0,5,4)]:
            ny, nx = y+dy, x+dx
            if 0<=ny<=59 and 0<=nx<=59:
                valid = True
                for i in range(5):
                    for j in range(5):
                        if grid[ny+i][nx+j] in [4, 5]:
                            valid = False
                            break
                    if not valid: break
                if valid and (ny, nx) not in visited:
                    visited.add((ny, nx))
                    q.append((ny, nx, path + [action]))
    return None
