def map_level():
    g = grids[-1]
    
    def can_fit_5x5(y, x):
        if y < 0 or y > 59 or x < 0 or x > 59: return False
        for r in range(y, y+5):
            for c in range(x, x+5):
                if g[r][c] in [4, 5]: return False
        return True
    
    q = [(15, 49)]
    visited = {(15, 49): []}
    
    while q:
        curr = q.pop(0)
        y, x = curr
        path = visited[curr]
        
        for dy, dx, action in [(-5, 0, '1'), (5, 0, '2'), (0, -5, '3'), (0, 5, '4')]:
            ny, nx = y + dy, x + dx
            if can_fit_5x5(ny, nx) and (ny, nx) not in visited:
                visited[(ny, nx)] = path + [action]
                q.append((ny, nx))
                
    print("Reachable tiles:")
    for tile, path in visited.items():
        print(f"{tile}: {path}")
