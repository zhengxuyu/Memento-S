def get_display(idx):
    mat = []
    for r in range(55, 61, 2):
        row = []
        for c in range(3, 9, 2):
            row.append(1 if grids[idx][r][c] == 9 else 0)
        mat.append(row)
    return mat
