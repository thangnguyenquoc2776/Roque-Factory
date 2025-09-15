import math, random, pygame
from .base import RobotBase, ROBOT_RADIUS

# Màu cho BAD robot
RED = (220, 64, 64)

class RobotBAD(RobotBase):
    USES_STATION_TS = True

    def __init__(self, *args,
                 fuse_time=5.0,
                 prod_penalty=1,
                 hp_penalty_on_explode=1,
                 hp_penalty_on_goal=1,
                 **kwargs):
        """
        BAD robot:
          - Sau fuse_time giây sẽ nổ → trừ production & HP.
          - Nếu đi hết đường mà chưa nổ → trừ HP theo hp_penalty_on_goal.
        """
        super().__init__(*args, **kwargs)

        # Tham số gameplay
        self.fuse_time = float(fuse_time) + random.uniform(-0.5, 0.5)  # lệch nhẹ để tránh nổ cùng lúc
        self.prod_penalty = int(prod_penalty)
        self.hp_penalty_on_explode = int(hp_penalty_on_explode)
        self.hp_penalty_on_goal = int(hp_penalty_on_goal)

        # Trạng thái runtime
        self._exploded = False
        self._escaped = False
        self.explosion_event = None  # gameplay sẽ đọc ở update()

    def is_bad(self) -> bool:
        return True

    def update(self, dt: float, stopped: bool):
        if not self.alive:
            return

        # Đếm ngược fuse_time
        self.fuse_time -= dt
        if self.fuse_time <= 0 and not self._exploded:
            self._exploded = True
            self.explosion_event = {
                "prod_penalty": self.prod_penalty,
                "hp_penalty": self.hp_penalty_on_explode,  # <<< trừ HP khi nổ
            }
            # play explosion SFX (BOOM)
            if getattr(self, "app", None) and getattr(self.app, "audio", None):
                try: self.app.audio.play_sfx("BOOM")
                except Exception: pass

            # Try to play VFX animation (if loaded in app.vfx). If found, set frames and
            # keep the robot alive until the VFX animation finishes.
            vframes = None
            if getattr(self, "app", None) and getattr(self.app, "vfx", None):
                # prefer common names, fallback to any available vfx
                vframes = self.app.vfx.get("BOOM")
                if not vframes:
                    # fallback to first available VFX list
                    for vv in self.app.vfx.values():
                        if vv:
                            vframes = vv
                            break

            if vframes:
               # use VFX frames as the sprite frames for a short non-looping animation
                self.frames = list(vframes)
                self.frame_index = 0
                self.frame_time = 0.0
                self.frame_duration = 0.12
                self.animation_loop = False
                # keep a timer to mark removal when VFX done
                self._playing_vfx = True
                self._vfx_time_left = float(self.frame_duration) * max(1, len(self.frames))
                # don't mark alive False yet — wait until VFX finishes
                return
            
            self.alive = False
            return

        # Di chuyển theo path
        super().update(dt, stopped)

        
        # If we are playing a VFX animation, count it down and remove when done
        if getattr(self, "_playing_vfx", False):
            self._vfx_time_left -= dt
            if self._vfx_time_left <= 0:
                self._playing_vfx = False
                self.alive = False
            return

        # Nếu về đích mà chưa nổ
        if not self.alive and self.t >= 1.0 and not self._exploded:
            self._escaped = True

    def draw(self, surf, pulse: float, debug=False):
        # If sprite frames exist (BAD_TRANS / BAD_LOOP), use base drawing so animation shows.
        if getattr(self, "frames", None):
            super().draw(surf, pulse, debug)
            return

        # fallback: red pulsing circle
        x, y = self.position()
        r = ROBOT_RADIUS + int(2 * math.sin(pulse * 6.283))
        pygame.draw.circle(surf, RED, (x, y), r)


    # def on_clicked(self):
    #     # Click = hạ gục, không nổ nữa
    #     # play shut_down SFX
    #     if getattr(self, "app", None) and getattr(self.app, "audio", None):
    #         try: self.app.audio.play_sfx("SHUT_DOWN")
    #         except Exception: pass
    
    #     self.alive = False
    #     self.explosion_event = None
    #     self._escaped = False
    #     return (True, True)

    def on_clicked(self):
        # Click = hạ gục, không nổ nữa
        # play shut_down SFX
        if getattr(self, "app", None) and getattr(self.app, "audio", None):
            try: self.app.audio.play_sfx("SHUT_DOWN")
            except Exception: pass

        # Try to play shutdown VFX (prefer SHUTDOWN -> BANG -> BOOM), otherwise remove immediately
        vframes = None
        if getattr(self, "app", None) and getattr(self.app, "vfx", None):
            vframes = self.app.vfx.get("EFFECT")
            if not vframes:
                for vv in self.app.vfx.values():
                    if vv:
                        vframes = vv
                        break

        if vframes:
            self.frames = list(vframes)
            self.frame_index = 0
            self.frame_time = 0.0
            # shorter duration for shutdown VFX: prefer per-vfx config if it's a dict with frame_duration,
            # otherwise use a short default (0.06s) so the VFX doesn't hang too long.
            cfg = getattr(self.app, "config", {}).get("vfx", {}).get("EFFECT", None)
            if isinstance(cfg, dict):
                self.frame_duration = float(cfg.get("frame_duration", 0.06))
            else:
                self.frame_duration = 0.06
            self.animation_loop = False
            # mark playing VFX; Robot.update must count this down and set alive=False afterwards
            self._playing_vfx = True
            self._vfx_time_left = float(self.frame_duration) * max(1, len(self.frames))
            # disable further explosion logic while playing VFX
            self._exploded = True
            self.explosion_event = None
            self._escaped = False
            return (True, False)  # handled, defer removal/award until VFX finishes

        # no vfx -> immediate removal
        self.alive = False
        self.explosion_event = None
        self._escaped = False
        return (True, True)

