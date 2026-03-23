def my_bfs3(sy, sx, ty, tx):
    from collections import deque
    q = deque([(sy, sx, [])])
    visited = set([(sy, sx)])
    
    def is_valid(y, x):
        if y < 0 or y > 61 or x < 0 or x > 61: return False
        for r in range(y, y+3):
            for c in range(x, x+3):
                if grid[r][c] not in [3, 0, 1, 8, 9, 12, 14, 11]:
                    return False
        return True

    while q:
        y, x, path = q.popleft()
        if y == ty and x == tx:
            return path
        for dy, dx, action in [(-3, 0, 1), (3, 0, 2), (0, -3, 3), (0, 3, 4)]:
            ny, nx = y + dy, x + dx
            if (ny, nx) not in visited and is_valid(ny, nx):
                visited.add((ny, nx))
                q.append((ny, nx, path + [action]))
    return "None"
