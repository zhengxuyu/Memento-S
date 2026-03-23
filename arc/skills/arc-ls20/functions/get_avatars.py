def get_avatars():
    res = {}
    for r in range(64):
        for c in range(64):
            if grid[r][c] not in [3, 4, 5, 11] and (r,c) not in res:
                # Find connected component
                comp = []
                q = [(r,c)]
                visited = {(r,c)}
                while q:
                    y, x = q.pop(0)
                    comp.append((y,x))
                    for dy, dx in [(-1,0),(1,0),(0,-1),(0,1)]:
                        ny,nx = y+dy, x+dx
                        if 0<=ny<64 and 0<=nx<64 and grid[ny][nx] not in [3,4,5,11] and (ny,nx) not in visited:
                            visited.add((ny,nx))
                            q.append((ny,nx))
                
                min_y = min(y for y,x in comp)
                max_y = max(y for y,x in comp)
                min_x = min(x for y,x in comp)
                max_x = max(x for y,x in comp)
                h, w = max_y - min_y + 1, max_x - min_x + 1
                
                # Check if this component has been added
                added = False
                for k,v in res.items():
                    if (min_y, min_x) == k:
                        added = True
                
                if not added:
                    res[(min_y, min_x)] = (h, w, [grid[y][x] for y,x in comp][:5])
    return res
