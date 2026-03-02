def astar_path(grid, sy, sx, ty, tx):
    from collections import deque
    Q = deque([(sy, sx, [])])
    visited = set([(sy, sx)])
    while Q:
        y, x, path = Q.popleft()
        if y == ty and x == tx:
            print("Found path:", path)
            return path
        for dy, dx, act in [(-5,0,1), (5,0,2), (0,-5,3), (0,5,4)]:
            ny, nx = y + dy, x + dx
            if 0 <= ny < 60 and 0 <= nx < 60:
                valid = True
                for i in range(5):
                    for j in range(5):
                        if ny+i >= 64 or nx+j >= 64: valid = False; break
                        if grid[ny+i][nx+j] in (4,5): valid = False; break
                    if not valid: break
                if valid and (ny, nx) not in visited:
                    visited.add((ny, nx))
                    Q.append((ny, nx, path+[act]))
    print("No path found.")
