def find_buttons():
    for r in range(0, 60, 5):
        for c in range(0, 60, 5):
            # check if there's any 0 or 1 inside
            has_01 = False
            for rr in range(5):
                for cc in range(5):
                    if grid[r+rr][c+cc] in [0, 1]:
                        has_01 = True
            if has_01:
                print(f"Cell {r},{c} has 0 or 1")
