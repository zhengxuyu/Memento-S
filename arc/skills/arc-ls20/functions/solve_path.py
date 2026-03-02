def solve_path(start_y, start_x, ty, tx):
    q = [(start_y, start_x, [])]
    visited = set([(start_y, start_x)])
    
    while q:
        y, x, path = q.pop(0)
        
        if y == ty and x == tx:
            return path
            
        for dy, dx, act in [(-5, 0, 'ACTION1'), (5, 0, 'ACTION2'), (0, -5, 'ACTION3'), (0, 5, 'ACTION4')]:
            ny, nx = y + dy, x + dx
            
            # Check if this 5x5 area is valid (colors 0,1,3,9,11,12) and not out of bounds
            if ny < 0 or ny + 4 >= 64 or nx < 0 or nx + 4 >= 64:
                continue
            
            valid = True
            for i in range(5):
                for j in range(5):
                    # We can step on 3, 0, 1, 9, 12, etc, but not 4, 5
                    if grid[ny+i][nx+j] in (4, 5):
                        valid = False
                        break
                if not valid: break
                
            if valid and (ny, nx) not in visited:
                visited.add((ny, nx))
                q.append((ny, nx, path + [act]))
                
    return None
