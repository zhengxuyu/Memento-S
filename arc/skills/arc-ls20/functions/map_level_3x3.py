def map_level_3x3():
    g = grids[-1]
    
    def can_fit(size, y, x):
        if y < 0 or y+size-1 > 63 or x < 0 or x+size-1 > 63: return False
        for r in range(y, y+size):
            for c in range(x, x+size):
                if g[r][c] in [4, 5]: return False
        return True
    
    # 3x3 avatar at 46, 30?
    if not can_fit(3, 46, 30):
        print("3x3 avatar can't fit at 46, 30?!")
    else:
        q = [(46, 30)]
        visited = {(46, 30): []}
        while q:
            y, x = q.pop(0)
            for dy, dx, action in [(-3, 0, '1'), (3, 0, '2'), (0, -3, '3'), (0, 3, '4')]:
                ny, nx = y + dy, x + dx
                if can_fit(3, ny, nx) and (ny, nx) not in visited:
                    visited[(ny, nx)] = visited[(y, x)] + [action]
                    q.append((ny, nx))
        print("Secondary avatar reachable:", len(visited))
        print("Secondary can reach button (11, 51)?", (11, 51) in visited)
        print("Secondary can reach (43, 30)?", (43, 30) in visited)
