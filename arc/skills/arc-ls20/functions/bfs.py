def bfs(start_y, start_x, start_size, grid, step_size):
    q = [(start_y, start_x, set())]
    visited = set([(start_y, start_x)])
    while q:
        y, x, path = q.pop(0)
        # return when we reach button 
        # Button is roughly at (11, 50) bounding box 11..13, 50..52
        if 10 <= y <= 15 and 48 <= x <= 53:
            return path
        for dy, dx, d_name in [(step_size, 0, 'D'), (-step_size, 0, 'U'), (0, step_size, 'R'), (0, -step_size, 'L')]:
            ny, nx = y + dy, x + dx
            if 0 <= ny <= 64-start_size and 0 <= nx <= 64-start_size:
                # check collision
                blocked = False
                for iy in range(start_size):
                    for ix in range(start_size):
                        if grid[ny+iy][nx+ix] in [4, 5]:
                            blocked = True
                            break
                    if blocked: break
                if not blocked and (ny, nx) not in visited:
                    visited.add((ny, nx))
                    new_path = path.copy()
                    new_path.add(d_name)
                    q.append((ny, nx, new_path))
    return None
