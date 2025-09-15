def first_bad_ahead_on_path(robots, current_robot, path_id, t_value, eps=1e-6):
    for r in robots:
        if r is current_robot:
            continue
        if getattr(r, "path_id", -1) != path_id:
            continue
        if getattr(r, "is_bad", lambda: False)() and getattr(r, "is_blocker", lambda: False)() and r.alive:
            if (r.t - t_value) >= -eps:
                return True
    return False
