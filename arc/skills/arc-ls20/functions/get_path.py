def get_path():
    path_button = bfs_path(40, 29, 45, 49)
    print("Path to button:", path_button)
    path_goal = bfs_path(40, 29, 40, 14)
    print("Path to goal (direct?):", path_goal)
