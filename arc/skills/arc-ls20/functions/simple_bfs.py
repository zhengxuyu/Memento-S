def simple_bfs(start_y, start_x, target_y, target_x, step, player_h, player_w):
    queue = [(start_y, start_x, [])]
    visited = set()
    while queue:
        cy, cx, path = queue.pop(0)
        if cy == target_y and cx == target_x:
            return path
        if (cy, cx) in visited: continue
        visited.add((cy, cx))
        for dy, dx, act in [(-step,0,'UP (1)'), (step,0,'DOWN (2)'), (0,-step,'LEFT (3)'), (0,step,'RIGHT (4)')]:
            ny, nx = cy+dy, cx+dx
            if 0 <= ny <= 64-player_h and 0 <= nx <= 64-player_w:
                overlap = any(grid[nr][nc] == 5 for nr in range(ny, ny+player_h) for nc in range(nx, nx+player_w))
                if not overlap:
                    queue.append((ny, nx, path + [act]))
    return None
