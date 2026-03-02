def show_5x5(sy, sx):
    q = [(sy, sx)]
    visited = {(sy, sx)}
    while q:
        y, x = q.pop(0)
        for dy, dx in [(-5,0), (5,0), (0,-5), (0,5)]:
            ny, nx = y+dy, x+dx
            if 0<=ny<=59 and 0<=nx<=59:
                if can_fit_5(grid, ny, nx) and (ny, nx) not in visited:
                    visited.add((ny,nx))
                    q.append((ny,nx))
    print("Reachable 5x5 centers:", sorted(list(visited)))
