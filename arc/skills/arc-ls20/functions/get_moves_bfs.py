def get_moves_bfs(sy, sx, ty, tx):
    from collections import deque
    q = deque([((sy, sx), [])])
    visited = set([(sy, sx)])
    grid = grids[-1]
    while q:
        (y, x), path = q.popleft()
        if y == ty and x == tx:
            return path
        for dy, dx, act in [(-5, 0, '1'), (5, 0, '2'), (0, -5, '3'), (0, 5, '4')]:
            ny, nx = y + dy, x + dx
            if 0 <= ny <= 59 and 0 <= nx <= 59:
                valid = True
                for i in range(5):
                    for j in range(5):
                        if grid[ny+i][nx+j] in (4, 5):
                            valid = False
                            break
                    if not valid:
                        break
                if valid and (ny, nx) not in visited:
                    visited.add((ny, nx))
                    q.append(((ny, nx), path + [act]))
    return None
