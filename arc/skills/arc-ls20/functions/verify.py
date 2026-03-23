def verify(grid):
    sy, sx = 25, 49
    print("blocked:", any(grid[24][sx+c] in [4,5] for c in range(5)))
