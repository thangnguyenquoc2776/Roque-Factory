import math
from typing import List, Tuple

Point = Tuple[int, int]
FPoint = Tuple[float, float]

def rescale_points(norm_pts: List[FPoint], width: int, height: int) -> List[Point]:
    return [(int(x*width), int(y*height)) for (x,y) in norm_pts]

def polyline_length(pts: List[Point]) -> float:
    tot = 0.0
    for i in range(len(pts)-1):
        x1,y1 = pts[i]; x2,y2 = pts[i+1]
        tot += math.hypot(x2-x1, y2-y1)
    return tot

def sample_path_t(points: List[Point], t: float, total_len: float=None) -> Point:
    if not points: return (0,0)
    if t <= 0: return points[0]
    if t >= 1: return points[-1]
    if total_len is None:
        total_len = polyline_length(points)
    target = t * total_len
    run = 0.0
    for i in range(len(points)-1):
        x1,y1 = points[i]; x2,y2 = points[i+1]
        seg = math.hypot(x2-x1, y2-y1)
        if run + seg >= target:
            k = (target - run) / seg if seg>0 else 0
            return (int(x1 + (x2-x1)*k), int(y1 + (y2-y1)*k))
        run += seg
    return points[-1]

def project_point_to_t(poly: List[Point], px: int, py: int) -> float:
    if not poly or len(poly) < 2:
        return 0.0
    total = polyline_length(poly)
    if total <= 1e-6:
        return 0.0
    best_tlen = 0.0
    run = 0.0
    best_dist2 = float("inf")
    for i in range(len(poly)-1):
        x1,y1 = poly[i]; x2,y2 = poly[i+1]
        vx, vy = x2-x1, y2-y1
        seg = vx*vx + vy*vy
        if seg <= 1e-9:
            continue
        wx, wy = px - x1, py - y1
        u = max(0.0, min(1.0, (wx*vx + wy*vy) / seg))
        projx, projy = x1 + u*vx, y1 + u*vy
        d2 = (px - projx)**2 + (py - projy)**2
        if d2 < best_dist2:
            best_dist2 = d2
            best_tlen = run + math.hypot(projx-x1, projy-y1)
        run += math.hypot(vx, vy)
    return max(0.0, min(1.0, best_tlen / total))
