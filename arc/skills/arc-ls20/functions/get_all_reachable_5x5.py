def get_all_reachable_5x5(sy, sx):
    # Valid sizes
    sz = 5
    q = [(sy,sx)]
    visited = {(sy,sx)}
    while q:
        y, x = q.pop(0)
        # Check directions (up, down, left, right)
        for dy, dx in [(-5,0), (5,0), (0,-5), (0,5)]:
            ny, nx = y+dy, x+dx
            if 0 <= ny <= 60 and 0 <= nx <= 60:
                # Check for color 4, 5, 11 (if 11 blocks 5x5)
                is_valid = True
                for r in range(ny, ny+5):
                    for c in range(nx, nx+5):
                        val = grid[r][c]
                        if val in [4, 5, 11]:
                            is_valid = False
                            break
                    if not is_valid: break
                if is_valid and (ny,nx) not in visited:
                    visited.add((ny,nx))
                    q.append((ny,nx))
    return visited
