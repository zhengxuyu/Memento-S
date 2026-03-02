def print_path():
    path = []
    for g in grids:
        path.append(get_player_pos(g))
    print(path)
