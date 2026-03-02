def get_all_reachable(grid, start_y, start_x):
    from collections import deque
    queue = deque([(start_y, start_x, [])])
    visited = set([(start_y, start_x)])
    
    while queue:
        y, x, path = queue.popleft()
            
        for dy, dx, act in [(-5, 0, 1), (5, 0, 2), (0, -5, 3), (0, 5, 4)]:
            ny, nx = y + dy, x + dx
            # simple bounds
            if 0 <= ny <= 59 and 0 <= nx <= 59:
                valid = True
                for i in range(5):
                    for j in range(5):
                        cy, cx = ny + i, nx + j
                        if grid[cy][cx] in [4, 5]:
                            valid = False
                            break
                    if not valid:
                        break
                if valid and (ny, nx) not in visited:
                    visited.add((ny, nx))
                    queue.append((ny, nx, path + [act]))
    return visited
