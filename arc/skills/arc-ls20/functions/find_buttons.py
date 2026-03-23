def find_buttons():
    buttons = []
    for r in range(62):
        for c in range(62):
            if grid[r][c] in [0, 1] and grid[r][c] != grid[r][c+1]:
                # check if it looks like a button
                window = [row[c:c+3] for row in grid[r:r+3]]
                s = sum(1 for row in window for val in row if val in [0, 1])
                if s >= 4:
                    buttons.append((r, c))
    return list(set(buttons))
