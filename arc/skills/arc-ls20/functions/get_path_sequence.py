def get_path_sequence(sy, sx, ty, tx):
    # sy, sx = top-left of player 5x5
    # ty, tx = target top-left
    queue = [(sy, sx, [])]
    visited = set([(sy, sx)])
    
    while queue:
        y, x, path = queue.pop(0)
        if y == ty and x == tx:
            return path
        
        for dy, dx, action in [(-5, 0, '1'), (5, 0, '2'), (0, -5, '3'), (0, 5, '4')]:
            ny, nx = y + dy, x + dx
            if 0 <= ny <= 59 and 0 <= nx <= 59:
                valid = True
                for rr in range(ny, ny+5):
                    for cc in range(nx, nx+5):
                        # valid if color 3, 0, 1, 9 (if it's goal or player), 12
                        v = grid[rr][cc]
                        if v in [4, 5]: # background or wall
                            valid = False
                if valid and (ny, nx) not in visited:
                    visited.add((ny, nx))
                    queue.append((ny, nx, path + [action]))
    return None
