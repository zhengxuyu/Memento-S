def bfs_combined():
    # state = (ay, ax, a3y, a3x, active_avatar, button_pressed)
    ay, ax = 35, 9
    a3y, a3x = 46, 30
    active_avatar = 0 # 0 for 5x5, 1 for 3x3
    button_pressed = False 
    
    q = [(ay, ax, a3y, a3x, active_avatar, button_pressed, [])]
    visited = {(ay, ax, a3y, a3x, active_avatar, button_pressed)}
    
    while q:
        ca_y, ca_x, c3_y, c3_x, active, btn, path = q.pop(0)
        
        if len(path) > 100:
            return path
            
        if ca_y == 55 and ca_x == 3:
            return path
            
        # Switch avatar
        n_active = 1 - active
        state = (ca_y, ca_x, c3_y, c3_x, n_active, btn)
        if state not in visited:
            visited.add(state)
            q.append((*state, path + [5]))
            
        moves = [(-1, 0, 1), (1, 0, 2), (0, -1, 3), (0, 1, 4)]
        if active == 0:
            for dy, dx, act in moves:
                ny, nx = ca_y + dy*5, ca_x + dx*5
                if ny < 0 or ny > 59 or nx < 0 or nx > 59:
                    continue
                valid = True
                grid = grids[1] if btn else grids[0] # assuming grids[0] has gates closed, grids[1] doesn't exist? wait
                
                for r in range(ny, ny+5):
                    for c in range(nx, nx+5):
                        val = grid[r][c]
                        if val == 4 or val == 5:
                            if btn:
                                # if button pressed, maybe some 5's are 3
                                pass
                            valid = False
                if valid:
                    state = (ny, nx, c3_y, c3_x, active, btn)
                    if state not in visited:
                        visited.add(state)
                        q.append((*state, path + [act]))
        else:
            for dy, dx, act in moves:
                ny, nx = c3_y + dy*3, c3_x + dx*3
                if ny < 0 or ny > 61 or nx < 0 or nx > 61:
                    continue
                valid = True
                grid = grids[0]
                for r in range(ny, ny+3):
                    for c in range(nx, nx+3):
                        if grid[r][c] == 4 or grid[r][c] == 5:
                            valid = False
                if valid:
                    n_btn = btn or (ny == 11 and nx == 50)
                    state = (ca_y, ca_x, ny, nx, active, n_btn)
                    if state not in visited:
                        visited.add(state)
                        q.append((*state, path + [act]))
    return None
