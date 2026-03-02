def find_path(sy, sx, ty, tx):
    from collections import deque
    q = deque()
    q.append((sy, sx, []))
    visited = set()
    visited.add((sy, sx))
    
    while q:
        y, x, path = q.popleft()
        if y == ty and x == tx:
            return path
            
        for dy, dx, act in [(-5, 0, 1), (5, 0, 2), (0, -5, 3), (0, 5, 4)]:
            ny, nx = y + dy, x + dx
            if 0 <= ny <= 59 and 0 <= nx <= 59:
                # check if 5x5 area is free of obstacle 5 and 4
                blocked = False
                for r in range(ny, ny+5):
                    for c in range(nx, nx+5):
                        if grid[r][c] in [4, 5]:
                            blocked = True
                            break
                    if blocked: break
                if not blocked and (ny, nx) not in visited:
                    visited.add((ny, nx))
                    q.append((ny, nx, path + [act]))
    return None
