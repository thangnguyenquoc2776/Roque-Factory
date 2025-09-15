import math, pygame
from .base import RobotBase, ROBOT_RADIUS

RED=(220,64,64)
ORANGE=(250,140,40)

class RobotBadExploder(RobotBase):
    USES_STATION_TS = True
    def __init__(self, *args, fuse_time=5.0, pause_time=5.0,
                 prod_penalty=1, hp_penalty_on_goal=1, **kwargs):
        super().__init__(*args, **kwargs)
        self.fuse_time = float(fuse_time)
        self.pause_time = float(pause_time)
        self.prod_penalty = int(prod_penalty)
        self.hp_penalty_on_goal = int(hp_penalty_on_goal)
        self._escaped = False
        self._exploded = False
        self.explosion_event = None

    def is_bad(self)->bool: return True

    def update(self, dt: float, stopped: bool):
        if not self.alive: return

        # ngòi nổ đếm thời gian (vẫn đếm khi pause hay không là do bạn muốn)
        self.fuse_time -= dt
        if self.fuse_time <= 0 and not self._exploded:
            self._exploded = True
            self.explosion_event = {"prod_penalty": self.prod_penalty,
                                    "pause_time": self.pause_time}
            self.alive = False
            return

        # di chuyển & dừng trạm theo băng chuyền
        super().update(dt, stopped)

        # nếu không nổ mà đã về đích
        if not self.alive and self.t >= 1.0 and not self._exploded:
            self._escaped = True

    def draw(self, surf, pulse: float, debug=False):
        x,y = self.position()
        flick = 0.5 + 0.5*math.sin(pulse*6.283*2.0)
        color = ORANGE if flick>0.5 else RED
        pygame.draw.circle(surf, color, (x,y), ROBOT_RADIUS+2)

    def on_clicked(self):
        self.alive = False
        self.explosion_event = None
        return (True, True)
