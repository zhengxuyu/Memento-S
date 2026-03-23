def find_path(sy, sx, size, step, color_obstacles):
    g = grids[1]
    q = [[(sy, sx)]]
    visited = set([(sy, sx)])
    actions = {
        (-step, 0): 'UP',
        (step, 0): 'DOWN',
        (0, -step): 'LEFT',
        (0, step): 'RIGHT'
    }
    
    while q:
        path = q.pop(0)
        y, x = path[-1]
        
        # Check if button is reached
        # Button bounds: 11..13, 50..52
        if 8 <= y <= 15 and 48 <= x <= 53:
            return path
            
        for dy, dx in [(-step, 0), (step, 0), (0, -step), (0, step)]:
            ny, nx = y + dy, x + dx
            if 0 <= ny <= 64-size and 0 <= nx <= 64-size:
                blocked = False
                for r in range(ny, ny+size):
                    for c in range(nx, nx+size):
                        if g[r][c] in color_obstacles:
                            blocked = True
                            break
                    if blocked: break
                
                if not blocked and (ny, nx) not in visited:
                    visited.add((ny, nx))
                    q.append(path + [(ny, nx)])
                    
    return None
