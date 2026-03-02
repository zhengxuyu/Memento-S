def get_path_to_button(grid, sy, sx):
    q = deque([(sy, sx, [])])
    visited = set([(sy, sx)])
    while q:
        cy, cx, path = q.popleft()
        
        # Check if overlaps button (color 0 or 1)
        overlaps = False
        for y in range(cy, cy+5):
            for x in range(cx, cx+5):
                if grid[y][x] in [0, 1]:
                    overlaps = True
                    break
            if overlaps: break
            
        if overlaps:
            return cy, cx, path
            
        for dy, dx, act in [(-5, 0, '1'), (5, 0, '2'), (0, -5, '3'), (0, 5, '4')]:
            ny, nx = cy + dy, cx + dx
            if check_valid(grid, ny, nx) and (ny, nx) not in visited:
                visited.add((ny, nx))
                q.append((ny, nx, path + [act]))
    return None
