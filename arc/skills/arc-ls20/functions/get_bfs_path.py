def get_bfs_path():
    sy, sx = 15, 49
    queue = [(sy, sx, [])]
    visited = set()
    while queue:
        y, x, path = queue.pop(0)
        if (y, x) in visited: continue
        visited.add((y, x))
        
        # Are we near the goal?
        if y >= 55 and x <= 14:
            print(f"Reached {y}, {x} with path {path}")
            return path
            
        for dy, dx, act in [(-5, 0, 1), (5, 0, 2), (0, -5, 3), (0, 5, 4)]:
            ny, nx = y + dy, x + dx
            if 0 <= ny <= 59 and 0 <= nx <= 59:
                # check if 5x5 area is clear of color 4 and 5
                clear = True
                for i in range(5):
                    for j in range(5):
                        if grids[-1][ny+i][nx+j] in (4, 5):
                            clear = False
                            break
                    if not clear: break
                if clear:
                    queue.append((ny, nx, path + [act]))
    print("No path found.")
