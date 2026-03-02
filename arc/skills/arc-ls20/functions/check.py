def check():
    for r in range(54, 62):
        for c in range(2, 10):
            if grid[r][c] == 9:
                print(f"pattern {r} {c}")
