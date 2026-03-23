def reachable_3x3(sy, sx):
    from collections import deque
    q = deque([(sy, sx)])
    visited = set([(sy, sx)])

    def is_valid(y, x):
        if y < 0 or y > 61 or x < 0 or x > 61: return False
        for r in range(y, y+3):
            for c in range(x, x+3):
                if grid[r][c] in [4, 5]:
                    return False
        return True

    while q:
        y, x = q.popleft()
        for dy, dx in [(-3, 0), (3, 0), (0, -3), (0, 3)]:
            ny, nx = y + dy, x + dx
            if (ny, nx) not in visited and is_valid(ny, nx):
                visited.add((ny, nx))
                q.append((ny, nx))
    return list(visited)
