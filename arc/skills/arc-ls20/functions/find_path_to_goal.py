        def find_path_to_goal(sy, sx):
            q = collections.deque([(sy, sx, [])])
            visited = set([(sy, sx)])
            
            while q:
                y, x, path = q.popleft()
                if y == gy - 1 and x == gx - 1:
                    return path
                
                for ny, nx, act in get_valid_moves_sim(y, x):
                    if (ny, nx) not in visited:
                        visited.add((ny, nx))
                        q.append((ny, nx, path + [act]))
            return None
