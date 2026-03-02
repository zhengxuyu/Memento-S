def get_path_real_current(sy, sx, ty, tx):
    from collections import deque
    q = deque([(sy, sx, 0, [])])
    visited = set()
    grid = grids[-1]
    
    while q:
        y, x, dist, path = q.popleft()
        if (y, x) == (ty, tx):
            print(f"Path found! Dist: {dist}, Path: {path}")
            return path
            
        if (y, x) in visited:
            continue
        visited.add((y, x))
        
        for dy, dx, act in [(-5, 0, 1), (5, 0, 2), (0, -5, 3), (0, 5, 4)]:
            ny, nx = y + dy, x + dx
            if 0 <= ny <= 59 and 0 <= nx <= 59:
                valid = True
                for i in range(5):
                    for j in range(5):
                        try:
                            c = grid[ny+i][nx+j]
                            if c in [4, 5]:
                                valid = False
                                break
                        except:
                            valid = False
                    if not valid:
                        break
                if valid:
                    q.append((ny, nx, dist + 1, path + [act]))
                    
    print("No path found.")
    return None
