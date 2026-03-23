def find_path_5(sy, sx, ty, tx, gr):
    visited = set()
    queue = [(sy, sx, [])]
    while queue:
        cy, cx, p = queue.pop(0)
        if (cy, cx) == (ty, tx): return p
        if (cy, cx) in visited: continue
        visited.add((cy, cx))
        for dy, dx, a in [(-5,0,1), (5,0,2), (0,-5,3), (0,5,4)]:
            ny, nx = cy+dy, cx+dx
            valid = True
            for r in range(ny, ny+5):
                for c in range(nx, nx+5):
                    if r<0 or r>=64 or c<0 or c>=64 or gr[r][c] in [4,5]:
                        valid = False            
            if valid: queue.append((ny, nx, p+[a]))
    return None
