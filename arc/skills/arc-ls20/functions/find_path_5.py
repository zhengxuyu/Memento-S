def find_path_5(grid, sy, sx, ty, tx, exact=False):
    from collections import deque
    queue = deque([(sy, sx, [])])
    visited = set([(sy, sx)])
    
    while queue:
        y, x, path = queue.popleft()
        
        if exact:
            if y == ty and x == tx:
                return path
        else:
            # Overlap with button at ty, tx
            # any point of the 5x5 player overlaps any part of the button?
            # button bounds: let's say (31,21)-(33,22) approx
            # button center is ~32,21. Overlap means:
            if abs((y+2) - 32) <= 3 and abs((x+2) - 21) <= 3:
                return path
                
        for move_name, dy, dx in [('U', -5, 0), ('D', 5, 0), ('L', 0, -5), ('R', 0, 5)]:
            ny, nx = y + dy, x + dx
            if (ny, nx) not in visited and can_fit_5(grid, ny, nx):
                visited.add((ny, nx))
                queue.append((ny, nx, path + [move_name]))
    return None
