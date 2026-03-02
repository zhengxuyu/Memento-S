def find_button(grid):
    # Button is 3x3 at 46,50 (target 45,49) or similar. Let's look for a cross of 1s or 0s.
    # Actually, we know level 2 button target top-left is 45, 49. Let's check if it's there.
    for r in range(60):
        for c in range(60):
            # check for 3x3 containing 1s
            has_1 = False
            for i in range(3):
                for j in range(3):
                    if grid[r+i][c+j] == 1:
                        has_1 = True
            if has_1:
                return (r-1, c-1) # Assuming it's centered in 5x5
    return None
