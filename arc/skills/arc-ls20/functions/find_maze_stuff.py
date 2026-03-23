def find_maze_stuff(g):
    import collections
    def is_valid_5x5(y, x):
        if y < 0 or y+4 > 63 or x < 0 or x+4 > 63: return False
        for dy in range(5):
            for dx in range(5):
                c = g[y+dy][x+dx]
                # button is at 11..13, 50..52 -> colors 0, 1. Assume they are walkable.
                if c == 4 or c == 5:
                    return False
        return True

    # BFS from 10,49 to 55,3
    q = collections.deque([(10, 49, [])])
    visited = set([(10, 49)])
    while q:
        y, x, path = q.popleft()
        if y == 55 and x == 4:
            print("Found 55,4!", path)
        if y == 55 and x == 3:
            print("Path to 55, 3:", path)
            return path
        
        for dy, dx, d_name in [(-5,0,1), (5,0,2), (0,-5,3), (0,5,4)]:
            ny, nx = y + dy, x + dx
            if is_valid_5x5(ny, nx):
                if (ny, nx) not in visited:
                    visited.add((ny, nx))
                    q.append((ny, nx, path + [d_name]))
    
    # If no path due to gate, check nearest U-shape
    print("Could not find direct path. Maybe blocked by gate.")
