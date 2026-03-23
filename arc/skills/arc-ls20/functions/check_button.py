def check_button(g):
    print("Button area:")
    for r in range(11, 15):
        print("".join(str(g[r][c]).ljust(3) for c in range(50, 54)))

    print("Secondary avatar currently at:")
    for r in range(11, 15):
        for c in range(50, 54):
            if g[r][c] in [0,1,8,14]:
                print(f"({r},{c}) color {g[r][c]}")
