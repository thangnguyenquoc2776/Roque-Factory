import pygame, random
from engine.state import State
from engine.geometry import rescale_points
from engine.render import draw_conveyor, draw_hud, draw_stations
from data.registry import ROBOT_TYPES
from .result import ResultState
import robots  # ensure registration
BG = (28, 34, 42)

class GameplayState(State):
    def enter(self, **kwargs):
        # Tốc độ băng chuyền chung
        self.conveyor_speed = float(self.app.config.get("defaults", {}).get("robot_speed", 0.12))

        # Level
        self.level_index = kwargs.get("level_index", 0)
        self.level = self.app.levels[self.level_index]

        # Map
        W, H = self.app.screen.get_size()
        self.map = self.app.maps.get(self.level.map)
        if not self.map:
            from data.schema import MapSpec, PathSpec, MapStationsCfg
            self.map = MapSpec(
                map_id="straight", name="Straight",
                paths=[PathSpec(points=[(0.08,0.5),(0.92,0.5)])],
                stations_cfg=MapStationsCfg(preset="straight_default")
            )

        # Lanes
        self.paths = [rescale_points(ps.points, W, H) for ps in self.map.paths]

        # Stations -> ts
        self.path_station_ts = []
        for i, _ in enumerate(self.map.paths):
            res = self.app.loader.resolve_stations_for_path(self.map, i, (W, H))
            ts = res["ts"] or [(k+1)/13 for k in range(12)]
            self.path_station_ts.append(ts)

        # Robot defs
        robots_defs = [(r.type, r.weight, r.params) for r in self.level.spawn.robots]

       
        #!fix
        self.spawners = [
            Spawner(self.level.spawn.interval, robots_defs, i, p, self.path_station_ts[i], self.conveyor_speed, app=self.app)
            for i, p in enumerate(self.paths)
        ]

        # Stats
        self.time_left = float(self.level.time)
        self.goal = int(self.level.goal)
        self.production = 0
        self.hp = int(self.app.config.get("defaults", {}).get("hp", 3))
        self.hits = 0
        self.misses = 0

        self.robots = []
        self.pulse = 0.0
        self.game_over = False
        self.win = False

    def accuracy(self):
        total = self.hits + self.misses
        return (self.hits/total)*100.0 if total>0 else 100.0

    def handle_event(self, e):
        # if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and not self.game_over:
        #     mx, my = pygame.mouse.get_pos()
        #     hit=False
        #     for r in reversed(self.robots):
        #         if r.is_bad() and r.alive and r.hit_test(mx,my):
        #             handled, counts = r.on_clicked()
        #             if handled:
        #                 hit=True
        #                 if counts: self.hits += 1
        #                 r.alive=False
        #                 break
        #     if not hit: self.misses += 1

        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and not self.game_over:
            mx, my = getattr(e, "pos", pygame.mouse.get_pos())
            hit = False
            for r in reversed(self.robots):
                if not (r.is_bad() and r.alive and r.hit_test(mx, my)):
                    continue
                res = r.on_clicked()
                if not res:
                    break
                handled, award_now = res
                if handled:
                    hit = True
                    if award_now:
                        # immediate award + remove
                        self.hits += 1
                        r.alive = False
                        try: self.robots.remove(r)
                        except ValueError: pass
                    else:
                        # deferred: VFX playing, do nothing now; Robot.update will clear alive when done
                        pass
                break
            if not hit:
                self.misses += 1

        if e.type == pygame.KEYDOWN:
            # Restart level
            if e.key == pygame.K_r:
                self.app.switch_state(GameplayState(self.app), level_index=self.level_index)
            # ESC -> quay về chọn level
            elif e.key == pygame.K_ESCAPE:
                from .level_select import LevelSelectState
                self.app.switch_state(LevelSelectState(self.app))
            # M -> quay về menu chính
            elif e.key == pygame.K_m:
                from .main_menu import MainMenuState
                self.app.switch_state(MainMenuState(self.app))

    def update(self, dt):
        if self.game_over: return

        # Time
        self.time_left -= dt
        if self.time_left <= 0:
            self.time_left = 0
            self.game_over = True
            self.win = (self.production >= self.goal)

        self.pulse = (self.pulse + dt) % 1.0

        # Spawn
        for sp in self.spawners:
            new_r = sp.try_spawn(dt)
            if new_r: self.robots.append(new_r)

        # Update robots
        self.robots.sort(key=lambda r:(getattr(r,"path_id",-1), r.t))
        for r in self.robots:
            r.update(dt, stopped=False)


        # Post-process: THAY THẾ robot mutate, xử lý về đích
        survivors = []
        hp_loss = 0
        prod_delta = 0
        for r in self.robots:
            if not r.alive:
                # Nếu vừa mutate thì thay thế
                new_r = getattr(r, "_mutated_into", None)
                if new_r is not None:
                    survivors.append(new_r)
                    continue

                if r.is_bad():
                    # BAD nổ → trừ production + HP
                    ev = getattr(r, "explosion_event", None)
                    if ev:
                        prod_delta -= int(ev.get("prod_penalty", 0))
                        hp_loss += int(ev.get("hp_penalty", 0))

                    # BAD lọt đích mà chưa nổ
                    elif getattr(r, "_escaped", False) or r.t >= 1.0:
                        hp_loss += int(getattr(r, "hp_penalty_on_goal", 1))
                else:
                    # OK về đích -> + production
                    self.production += 1
            else:
                survivors.append(r)

        self.robots = survivors

        # Áp dụng
        if prod_delta != 0:
            self.production = max(0, self.production + prod_delta)
        if hp_loss > 0:
            self.hp -= hp_loss
            if self.hp <= 0:
                self.hp = 0
                self.game_over = True
                self.win = False

        # Win
        if self.production >= self.goal:
            self.game_over = True
            self.win = True

        if self.game_over:
            #self.app.switch_state(ResultState(self.app), win=self.win)
            # go to result state with stats
            self.some_end_game_path()

    def draw(self, screen):
        screen.fill(BG)
        for i, path in enumerate(self.paths):
            draw_conveyor(screen, path, width=24)
            if self.path_station_ts[i]:
                draw_stations(screen, path, self.path_station_ts[i])  # bản dùng ts

        for r in self.robots:
            r.draw(screen, pulse=self.pulse, debug=False)

        draw_hud(screen, self.app.font,
                 self.time_left, self.production, self.goal,
                 self.hp, self.accuracy(),
                 self.hits, self.misses)

        # Hint các nút
        hint1 = self.app.font.render("[R] Restart", True, (200, 200, 200))
        hint2 = self.app.font.render("[ESC] Level Select", True, (200, 200, 0))
        hint3 = self.app.font.render("[M] Main Menu", True, (255, 150, 150))
        screen.blit(hint1, (20, 60))
        screen.blit(hint2, (20, 90))
        screen.blit(hint3, (20, 120))

        
    def some_end_game_path(self):
        # collect stats from gameplay and switch to ResultState
        stats = {
            "hits": getattr(self, "hits", 0),
            "misses": getattr(self, "misses", 0),
            "accuracy": self.accuracy(),
            "production": getattr(self, "production", 0),
            "goal": getattr(self, "goal", 0),
            "time_left": getattr(self, "time_left", 0),
            "hp": getattr(self, "hp", 0),
        }
        # pass app and stats to ResultState
        self.app.switch_state(ResultState(self.app), stats=stats, win=self.win, app=self.app)

class Spawner:

    #!fix
    def __init__(self, interval, robots_defs, path_id, path_pts, station_ts, speed, app=None):
        self.interval = interval
        self.timer = 0.0
        self.robot_defs = robots_defs
        self.path_id = path_id
        self.path_pts = path_pts
        self.station_ts = list(station_ts)
        self.speed = float(speed)
        self.app = app

    def _weighted_choice(self):
        total = sum(w for _,w,_ in self.robot_defs) or 1.0
        r = random.random() * total
        acc = 0.0
        for t, w, p in self.robot_defs:
            acc += w
            if r <= acc:
                return (t, p)
        return self.robot_defs[-1][0], self.robot_defs[-1][2]

    def try_spawn(self, dt):
        self.timer += dt
        if self.timer >= self.interval:
            self.timer -= self.interval
            t, params = self._weighted_choice()
            cls = ROBOT_TYPES.get(t.upper())
            if cls:
                spawn_params = dict(params)
                if getattr(cls, "USES_STATION_TS", True):
                    spawn_params.setdefault("station_ts", self.station_ts)
                spawn_params.setdefault("dwell_time_station", params.get("dwell_time_station", 0.35))
                spawn_params["speed"] = self.speed  # ép tốc độ băng chuyền thống nhất
                # return cls(path_id=self.path_id, path_pts=self.path_pts, **spawn_params)
            
                #! pass app and type_name so robots can access sprites/animation
                extra = {"app": self.app, "type_name": t.upper()}
                spawn_params.update(extra)
                return cls(path_id=self.path_id, path_pts=self.path_pts, **spawn_params)
        return None
    
    
