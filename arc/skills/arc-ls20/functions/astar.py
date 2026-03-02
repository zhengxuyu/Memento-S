def astar(start_y, start_x, target_y, target_x, obstacle_color, grid):
    import collections
    queue = collections.deque([(start_y, start_x, [])])
    visited = {(start_y, start_x)}
    
    while queue:
        y, x, path = queue.popleft()
        
        if y == target_y and x == target_x:
            return path
            
        for dy, dx, action in [(-5, 0, 1), (5, 0, 2), (0, -5, 3), (0, 5, 4)]:
            ny, nx = y + dy, x + dx
            
            if 0 <= ny < 64 and 0 <= nx < 64 and (ny, nx) not in visited:
                # Check 5x5 block
                hit_obstacle = False
                for by in range(ny, ny + 5):
                    for bx in range(nx, nx + 5):
                        if 0 <= by < 64 and 0 <= bx < 64:
                            if grid[by][bx] == obstacle_color:
                                hit_obstacle = True
                                break
                    if hit_obstacle:
                        break
                        
                if not hit_obstacle:
                    visited.add((ny, nx))
                    queue.append((ny, nx, path + [action]))
                    
    return None
