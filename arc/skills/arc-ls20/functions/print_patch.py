def print_patch(sy, ey, sx, ex):
    for r in range(max(0, sy), min(64, ey)):
        print("".join(f"{grid[r][c]:2d}" for c in range(max(0, sx), min(64, ex))))
