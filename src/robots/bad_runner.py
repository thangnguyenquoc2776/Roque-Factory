import pygame
from .base import RobotBase, ROBOT_RADIUS

PURPLE=(150,90,200)

class RobotBadRunner(RobotBase):
    USES_STATION_TS = True
    def __init__(self, *args, hp_penalty_on_goal=3, **kwargs):
        super().__init__(*args, **kwargs)
        self.hp_penalty_on_goal = int(hp_penalty_on_goal)
        self._escaped = False

    def is_bad(self)->bool: return True

    def update(self, dt: float, stopped: bool):
        if not self.alive: return
        # chạy & dừng theo băng chuyền
        super().update(dt, stopped)
        # đến đích thì coi như “lọt”
        if not self.alive and self.t >= 1.0:
            self._escaped = True

    def draw(self, surf, pulse: float, debug=False):
        x,y = self.position()
        pygame.draw.circle(surf, PURPLE, (x,y), ROBOT_RADIUS+1)

    def on_clicked(self):
        self.alive = False
        return (True, True)
