def get_reachable(grid, sy, sx):
    from collections import deque
    Q = deque([(sy, sx, [])])
    visited = set([(sy, sx)])
    reachable = []
    while Q:
        y, x, path = Q.popleft()
        reachable.append((y, x))
        for dy, dx, act in [(-5,0,1), (5,0,2), (0,-5,3), (0,5,4)]:
            ny, nx = y + dy, x + dx
            if 0 <= ny < 60 and 0 <= nx < 60:
                valid = True
                for i in range(5):
                    for j in range(5):
                        if grid[ny+i][nx+j] in (4,5): valid = False; break
                    if not valid: break
                if valid and (ny, nx) not in visited:
                    visited.add((ny, nx))
                    Q.append((ny, nx, path+[act]))
    
    print("Reachable points:", reachable)
