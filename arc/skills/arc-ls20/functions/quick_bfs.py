def quick_bfs(y, x, ty, tx):
    from collections import deque
    q = deque([(y, x, [])])
    visited = set([(y, x)])
    while q:
        cy, cx, path = q.popleft()
        if cy == ty and cx == tx:
            return path
        for dy, dx, action in [(-5, 0, '1'), (5, 0, '2'), (0, -5, '3'), (0, 5, '4')]:
            ny, nx = cy + dy, cx + dx
            if 0 <= ny <= 59 and 0 <= nx <= 59:
                valid = True
                for r in range(ny, ny+5):
                    for c in range(nx, nx+5):
                        if grid[r][c] not in [0, 1, 3, 9, 12]:
                            valid = False
                if valid and (ny, nx) not in visited:
                    visited.add((ny, nx))
                    q.append((ny, nx, path + [action]))
    return None
