def check_obs():
    sy, sx = 30, 34
    ty, tx = 30, 29
    blocked = False
    for r in range(ty, ty+5):
        for c in range(tx, tx+5):
            if grid[r][c] == 5:
                print(f"Blocked at {r}, {c}")
                blocked = True
    if not blocked: print("Not blocked")
