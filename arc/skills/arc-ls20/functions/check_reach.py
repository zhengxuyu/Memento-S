def check_reach():
    q = [(25, 9)]
    vis = {(25, 9): None}
    while q:
        y, x = q.pop(0)
        for dy, dx, act in [(-5, 0, '1'), (5, 0, '2'), (0, -5, '3'), (0, 5, '4')]:
            ny, nx = y+dy, x+dx
            if 0 <= ny and ny+5 <= 64 and 0 <= nx and nx+5 <= 64:
                valid = True
                for r in range(ny, ny+5):
                    for c in range(nx, nx+5):
                        if grid[r][c] in [4, 5]:
                            valid = False
                            break
                    if not valid: break
                if valid and (ny, nx) not in vis:
                    vis[(ny, nx)] = (y, x, act)
                    q.append((ny, nx))
    return vis
