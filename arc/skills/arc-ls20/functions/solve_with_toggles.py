def solve_with_toggles(g1, g2, start_y, start_x, ty, tx):
    q = [(start_y, start_x, 1, [])]
    visited = {(start_y, start_x, 1)}
    moves = [(-5,0,1), (5,0,2), (0,-5,3), (0,5,4), (0,0,5)]
    while q:
        y, x, state, path = q.pop(0)
        if y == ty and x == tx:
            return path
        grid = g1 if state == 0 else g2
        for dy, dx, action in moves:
            if action == 5:
                # toggle
                ny, nx, nstate = y, x, 1 - state
                if (ny, nx, nstate) not in visited:
                    visited.add((ny, nx, nstate))
                    q.append((ny, nx, nstate, path + [action]))
                continue
            
            ny, nx = y + dy, x + dx
            valid = True
            if ny < 0 or ny > 59 or nx < 0 or nx > 59:
                valid = False
            else:
                for r in range(ny, ny+5):
                    for c in range(nx, nx+5):
                        if grid[r][c] in [4, 5]:
                            valid = False
            if valid and (ny, nx, state) not in visited:
                visited.add((ny, nx, state))
                q.append((ny, nx, state, path + [action]))
    return None
