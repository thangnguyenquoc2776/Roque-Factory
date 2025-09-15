from dataclasses import dataclass, field
from typing import Any, List, Tuple, Optional, Type
import pygame
from engine.geometry import sample_path_t

TEAL = (18,148,152)
YELLOW = (243,198,62)
ROBOT_RADIUS = 22

@dataclass
class RobotBase:
    # Quỹ đạo
    path_id: int
    path_pts: List[Tuple[int,int]]

    # Tiến độ dọc path (0..1)
    t: float = 0.0
    alive: bool = True

    # Trạm dừng
    station_ts: List[float] = field(default_factory=list)
    dwell_time_station: float = 0.35
    _next_station_idx: int = 0
    _dwell_left: float = 0.0

    # Tốc độ băng chuyền dùng chung
    speed: float = 0.12

    # Biến đổi (OK -> BAD)
    _mutated_into: Optional["RobotBase"] = None
    _mutated_flag: bool = False

    # --- added fields for app + animation ---
    app: Optional[Any] = field(default=None, repr=False)
    type_name: str = field(default="", repr=False)
    
    # optional per-instance scale override: float scale factor or [w,h]
    sprite_scale: Optional[Any] = field(default=None, repr=False)

    # animation
    frames: List[Any] = field(default_factory=list, repr=False)   # list of pygame.Surface
    frame_index: int = 0
    frame_time: float = 0.0
    frame_duration: float = 0.12
    animation_loop: bool = True

    # transition control (used when created by mutate_to to play BAD_TRANS then BAD_LOOP)
    start_transition: bool = False
    _is_converting: bool = False
    _post_transition_frames: List[Any] = field(default_factory=list, repr=False)
    _post_transition_duration: float = 0.18

    # ---------- Hooks ----------
    def is_bad(self) -> bool: return False
    def is_stopped(self) -> bool: return False
    def on_reach_station(self, station_idx: int): pass

    def mutate_to(self, cls: Type["RobotBase"], **kwargs):
        """
        Tạo robot mới thay thế robot hiện tại, GIỮ NGUYÊN:
          - t (tiến độ), speed (tốc độ băng chuyền)
          - station_ts (danh sách trạm)
          - _next_station_idx, _dwell_left (tiến độ trạm hiện tại)
        """
        # self._mutated_into = cls(
        #     path_id=self.path_id,
        #     path_pts=self.path_pts,
        #     t=self.t,
        #     alive=True,
        #     station_ts=self.station_ts,
        #     dwell_time_station=self.dwell_time_station,
        #     speed=self.speed,
        #     _next_station_idx=self._next_station_idx,  # <<< giữ trạm hiện tại
        #     _dwell_left=self._dwell_left,              # <<< giữ thời gian dwell nếu đang dừng
        #     **kwargs
        # )
        # self.alive = False  # robot cũ “chết”, chỉ còn con mới

        # ensure new instance sees the same app (so it can load sprites)
        kwargs.setdefault("app", getattr(self, "app", None))
        # request the new instance start with BAD transition animation (caller may override)
        kwargs.setdefault("start_transition", True)

        self._mutated_into = cls(
            path_id=self.path_id,
            path_pts=self.path_pts,
            t=self.t,
            alive=True,
            station_ts=self.station_ts,
            dwell_time_station=self.dwell_time_station,
            speed=self.speed,
            _next_station_idx=self._next_station_idx,  # <<< giữ trạm hiện tại
            _dwell_left=self._dwell_left,              # <<< giữ thời gian dwell nếu đang dừng
            **kwargs
        )
        
        self._mutated_flag = True
        self.alive = False  # robot cũ “chết”, chỉ còn con mới

    def get_speed(self) -> float:
        return float(self.speed)
    
    def __post_init__(self):
        # initialize animation frames using app.sprites if available
        if getattr(self, "app", None) and getattr(self.app, "sprites", None):
            spr = self.app.sprites
            # If explicitly asked to start transition, set BAD_TRANS then schedule BAD_LOOP
            if self.start_transition:
                trans = spr.get("BAD_TRANS", [])
                loop = spr.get("BAD_LOOP", [])
                if trans:
                    self.frames = list(trans)
                    self.frame_index = 0
                    self.frame_time = 0.0
                    # slow transition frames
                    self.frame_duration = 0.45
                    self.animation_loop = False
                    self._is_converting = True
                    self._post_transition_frames = list(loop) if loop else []
                    self._post_transition_duration = 0.18
                    return
            # Otherwise try to pick default frames by type or class
            # Prefer explicit type_name if provided
            key = (self.type_name or self.__class__.__name__).upper()
            if "OK" in key and "OK" in spr:
                self.frames = list(spr.get("OK", []))
            elif "BAD" in key and spr.get("BAD_LOOP"):
                # bad robots created normally (not via transition) get loop frames
                self.frames = list(spr.get("BAD_LOOP", []))
                self.frame_duration = 0.18
                self.animation_loop = True

    def update(self, dt: float, stopped: bool):
        # animation tick (before movement)
        if self.frames:
            self.frame_time += dt
            if self.frame_time >= self.frame_duration:
                self.frame_time -= self.frame_duration
                self.frame_index += 1
                if self.frame_index >= len(self.frames):
                    if self.animation_loop:
                        self.frame_index = 0
                    else:
                        # non-loop animation ended
                        if self._is_converting and self._post_transition_frames:
                            # switch to post-transition loop (BAD_LOOP)
                            self.frames = list(self._post_transition_frames)
                            self.frame_index = 0
                            self.frame_time = 0.0
                            self.frame_duration = float(self._post_transition_duration)
                            self.animation_loop = True
                            self._is_converting = False
                        else:
                            self.frame_index = len(self.frames) - 1
        if not self.alive: return

        # Đang dừng tại trạm
        if self._dwell_left > 0:
            self._dwell_left -= dt
            if self._dwell_left <= 0:
                self._dwell_left = 0.0
                self._next_station_idx += 1
            return

        # Dừng do global-pause hoặc loại tự khóa
        if stopped or self.is_stopped():
            return

        # Di chuyển dọc path
        self.t += self.get_speed() * dt
        if self.t >= 1.0:
            self.t = 1.0
            self.alive = False
            return

        # Snap vào các trạm bị vượt
        sts = self.station_ts or []
        while self._next_station_idx < len(sts) and self.t >= sts[self._next_station_idx]:
            self.t = sts[self._next_station_idx]
            self.on_reach_station(self._next_station_idx)

            # Nếu vừa mutate, dừng ngay để chuyển giao cho robot mới
            if not self.alive:
                return

            # Nếu không tự khóa -> dừng dwell tại trạm
            if not self.is_stopped():
                self._dwell_left = self.dwell_time_station
                return  # đứng yên tại trạm trong dwell

    def position(self) -> Tuple[int,int]:
        return sample_path_t(self.path_pts, self.t)

    def draw(self, surf, pulse: float, debug=False):
        # draw sprite if available
        if self.frames:
            x,y = self.position()
            img = self.frames[max(0, min(self.frame_index, len(self.frames)-1))]
            # only blit if it's a pygame.Surface; try to load if it looks like a path; otherwise fallback
            if isinstance(img, pygame.Surface):
                rect = img.get_rect(center=(x,y))
                surf.blit(img, rect)
                if debug:
                    pygame.draw.circle(surf, YELLOW, (x,y), ROBOT_RADIUS, 1)
                return
            else:
                # attempt to load if img is a path-like string
                try:
                    loaded = pygame.image.load(img).convert_alpha()
                    # cache loaded surface back into frames
                    self.frames[max(0, min(self.frame_index, len(self.frames)-1))] = loaded
                    rect = loaded.get_rect(center=(x,y))
                    surf.blit(loaded, rect)
                    if debug:
                        pygame.draw.circle(surf, YELLOW, (x,y), ROBOT_RADIUS, 1)
                    return
                except Exception:
                    # loading failed -> fallback to circle
                    pass

        # fallback visual
        x,y = self.position()
        pygame.draw.circle(surf, TEAL, (x,y), ROBOT_RADIUS)
        if debug:
            pygame.draw.circle(surf, YELLOW, (x,y), ROBOT_RADIUS, 1)

    def hit_test(self, mx, my) -> bool:
        x, y = self.position()
        return (mx-x)**2 + (my-y)**2 <= ROBOT_RADIUS**2

    def on_clicked(self):
        return (False, False)
