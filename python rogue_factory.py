import math
import random
import sys
import pygame

# =====================#
# Rogue Factory - MVP  #
# Tech Lead: bạn đồng hành
# =====================#

# --- Config màn hình & gameplay ---
WIDTH, HEIGHT = 1280, 720
FPS = 60

# Level presets (gợi ý 5 màn ~2-3 phút)
LEVELS = [
    # (duration_sec, spawn_interval, glitch_chance, goal)
    (120, 1.60, 0.08, 25),   # L1
    (135, 1.40, 0.12, 32),   # L2
    (150, 1.20, 0.16, 40),   # L3
    (150, 1.00, 0.20, 48),   # L4
    (165, 0.90, 0.24, 58),   # L5
]

BAD_FREEZE_TIME = 5.0   # BAD dừng 5s rồi escape nếu không bị click
ROBOT_SPEED = 0.12      # tốc độ t/giây (cân bằng sơ bộ)
ROBOT_RADIUS = 22
CONVEYOR_WIDTH = 24

# DDA theo Accuracy
MISS_HEAT_PER_MISS = 0.02   # +2% glitch chance mỗi miss
MISS_HEAT_DECAY = 0.20      # mỗi giây giảm 0.20 "heat"
MAX_EXTRA_GLITCH = 0.12     # cộng dồn không quá +12%

# Màu
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
UI_BG = (18, 22, 26)
TEAL = (18, 148, 152)
GRAY = (90, 99, 110)
YELLOW = (243, 198, 62)
RED = (220, 64, 64)
STEEL = (60, 80, 100)
CREAM = (244, 244, 236)

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Rogue Factory — MVP")
clock = pygame.time.Clock()
font = pygame.font.SysFont("arialrounded", 24)
big_font = pygame.font.SysFont("arialrounded", 48)

# --- Định nghĩa đường băng chuyền: polyline (tọa độ chuẩn hóa 0..1) ---
S_PATH = [
    (0.10, 0.30),
    (0.40, 0.30),
    (0.60, 0.55),
    (0.40, 0.80),
    (0.85, 0.80)
]

def lerp(a, b, t):
    return a + (b - a) * t

def polyline_length(points):
    """Tổng chiều dài polyline (px)."""
    total = 0.0
    for i in range(len(points) - 1):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        dx, dy = x2 - x1, y2 - y1
        total += math.hypot(dx, dy)
    return total

def rescale_points(norm_pts):
    """Đưa điểm [0..1] về pixel screen."""
    return [(int(x * WIDTH), int(y * HEIGHT)) for (x, y) in norm_pts]

PIX_PATH = rescale_points(S_PATH)
PATH_LENGTH = polyline_length(PIX_PATH)

def sample_path_t(points, t):
    """
    Lấy vị trí theo tham số t∈[0..1] dọc polyline đều theo chiều dài.
    """
    if t <= 0:
        return points[0]
    if t >= 1:
        return points[-1]
    target_len = t * PATH_LENGTH
    run = 0.0
    for i in range(len(points) - 1):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        seg = math.hypot(x2 - x1, y2 - y1)
        if run + seg >= target_len:
            k = (target_len - run) / seg
            return (int(lerp(x1, x2, k)), int(lerp(y1, y2, k)))
        run += seg
    return points[-1]

class Robot:
    __slots__ = ("t", "is_bad", "bad_timer", "alive", "escaped", "pos")

    def __init__(self, is_bad=False):
        self.t = 0.0
        self.is_bad = is_bad
        self.bad_timer = BAD_FREEZE_TIME if is_bad else 0.0
        self.alive = True
        self.escaped = False
        self.pos = sample_path_t(PIX_PATH, self.t)

    def update(self, dt, stopped):
        """
        Cập nhật robot:
        - Nếu BAD: đếm lùi; không di chuyển khi bad_timer > 0 (đang 'đứng yên').
        - Nếu stopped (có BAD phía trước): không di chuyển.
        - Ngược lại, tăng t theo tốc độ.
        """
        if not self.alive:
            return

        if self.is_bad and self.bad_timer > 0:
            self.bad_timer -= dt
            if self.bad_timer <= 0:
                # Hết thời gian → escape
                self.escaped = True
                self.alive = False
            return

        if stopped:
            # bị chặn bởi BAD phía trước
            return

        # di chuyển dọc đường
        self.t += ROBOT_SPEED * dt
        if self.t >= 1.0:
            self.t = 1.0
            self.alive = False  # rời băng chuyền ở đuôi (OK = +Production)
        self.pos = sample_path_t(PIX_PATH, self.t)

    def draw(self, surf, debug=False, pulse=0.0):
        x, y = self.pos
        if self.is_bad:
            # BAD nhấp nháy nhẹ để telegraph
            r = ROBOT_RADIUS + int(2 * math.sin(pulse * 6.283))
            pygame.draw.circle(surf, RED, (x, y), r)
        else:
            pygame.draw.circle(surf, TEAL, (x, y), ROBOT_RADIUS)

        if debug:
            # hit circle
            pygame.draw.circle(surf, YELLOW, (x, y), ROBOT_RADIUS, 1)

    def hit_test(self, mx, my):
        x, y = self.pos
        return (mx - x) ** 2 + (my - y) ** 2 <= (ROBOT_RADIUS) ** 2

class Spawner:
    def __init__(self, spawn_interval, glitch_chance):
        self.base_interval = spawn_interval
        self.timer = 0.0
        self.base_glitch = glitch_chance
        self.miss_heat = 0.0  # tăng tỉ lệ glitch tạm thời khi miss

    def dda_glitch(self):
        return min(self.base_glitch + self.miss_heat, self.base_glitch + MAX_EXTRA_GLITCH)

    def update_heat(self, dt):
        if self.miss_heat > 0:
            self.miss_heat = max(0.0, self.miss_heat - MISS_HEAT_DECAY * dt)

    def add_miss_heat(self):
        self.miss_heat = min(self.miss_heat + MISS_HEAT_PER_MISS, MAX_EXTRA_GLITCH)

    def try_spawn(self, dt):
        self.timer += dt
        spawned = None
        if self.timer >= self.base_interval:
            self.timer -= self.base_interval
            is_bad = random.random() < self.dda_glitch()
            spawned = Robot(is_bad=is_bad)
        return spawned

class Game:
    def __init__(self, level_index=0):
        # Level params
        self.level_index = level_index
        self.time_left, spawn_interval, glitch_chance, self.goal = LEVELS[level_index]

        self.hp = 3
        self.production = 0
        self.hits = 0
        self.misses = 0

        self.robots = []
        self.spawner = Spawner(spawn_interval, glitch_chance)

        self.debug = False
        self.elapsed = 0.0
        self.pulse = 0.0  # cho hiệu ứng nhấp nháy BAD

        self.game_over = False
        self.win = False

    def accuracy(self):
        total = self.hits + self.misses
        return (self.hits / total) * 100.0 if total > 0 else 100.0

    def first_bad_ahead_of(self, t_value):
        """
        Có BAD nào ở phía trước (t lớn hơn) không?
        """
        for r in self.robots:
            if r.is_bad and r.alive and r.t > t_value and r.bad_timer > 0:
                return True
        return False

    def update(self, dt):
        if self.game_over:
            return

        self.time_left -= dt
        self.elapsed += dt
        self.pulse = (self.pulse + dt) % 1.0

        # DDA heat giảm dần theo thời gian
        self.spawner.update_heat(dt)

        # Spawn
        new_r = self.spawner.try_spawn(dt)
        if new_r is not None:
            self.robots.append(new_r)

        # Sort theo t để logic "phía trước/phía sau" ổn định
        self.robots.sort(key=lambda r: r.t)

        # Cập nhật robot
        produced_now = 0
        hp_loss_now = 0
        for r in self.robots:
            if not r.alive:
                continue
            # stopped nếu có BAD phía trước
            stop_me = self.first_bad_ahead_of(r.t)
            r.update(dt, stopped=stop_me)

        # Hậu xử lý robot chết/thoát/cuối băng
        survivors = []
        for r in self.robots:
            if not r.alive:
                if r.is_bad:
                    if r.escaped:
                        hp_loss_now += 1
                    # BAD chết/thoát → bỏ
                else:
                    # OK đi hết băng → Production+1
                    self.production += 1
            else:
                survivors.append(r)
        self.robots = survivors

        if hp_loss_now > 0:
            self.hp -= hp_loss_now
            if self.hp <= 0:
                self.hp = 0
                self.game_over = True
                self.win = False

        # Thắng/thua theo thời gian/goal
        if self.production >= self.goal:
            self.game_over = True
            self.win = True
        elif self.time_left <= 0:
            self.game_over = True
            self.win = self.production >= self.goal

    def handle_click(self, mx, my):
        if self.game_over:
            return
        # Ưu tiên hit vào BAD (t gần nhất phía trước màn hình)
        hit_any_bad = False
        # Duyệt ngược (ưu tiên robot có t lớn hơn - "trên" màn hình)
        for r in reversed(self.robots):
            if r.is_bad and r.alive and r.bad_timer > 0 and r.hit_test(mx, my):
                r.alive = False  # shutdown ngay
                r.escaped = False
                hit_any_bad = True
                self.hits += 1
                break
        if not hit_any_bad:
            self.misses += 1
            self.spawner.add_miss_heat()  # DDA: miss làm tăng tỷ lệ BAD tạm thời

    def reset(self):
        self.__init__(level_index=self.level_index)

    def next_level(self):
        if self.level_index + 1 < len(LEVELS):
            self.__init__(level_index=self.level_index + 1)
        else:
            self.__init__(level_index=0)

    def draw_conveyor(self, surf):
        # vẽ dải băng chuyền (một đường dày)
        pygame.draw.lines(surf, STEEL, False, PIX_PATH, CONVEYOR_WIDTH)
        # vạch biên mảnh để dễ đọc
        pygame.draw.lines(surf, BLACK, False, PIX_PATH, 2)

        # các station nho nhỏ
        seg_dots = 12
        for i in range(seg_dots + 1):
            p = sample_path_t(PIX_PATH, i / seg_dots)
            pygame.draw.circle(surf, GRAY, p, 6)

    def draw_hud(self, surf):
        # thanh trên cùng
        pygame.draw.rect(surf, UI_BG, (0, 0, WIDTH, 48))
        t_text = font.render(f"Time: {max(0,int(self.time_left))}s", True, CREAM)
        pg_text = font.render(f"Production: {self.production}/{self.goal}", True, CREAM)
        hp_text = font.render(f"HP: {self.hp}", True, CREAM)
        acc_text = font.render(f"Acc: {self.accuracy():.0f}%", True, CREAM)

        surf.blit(t_text, (16, 12))
        surf.blit(pg_text, (WIDTH//2 - pg_text.get_width()//2, 12))
        right_x = WIDTH - 16
        surf.blit(acc_text, (right_x - acc_text.get_width(), 12))
        right_x -= acc_text.get_width() + 16
        surf.blit(hp_text, (right_x - hp_text.get_width(), 12))

        # cảnh báo khi còn < 5s
        if 0 < self.time_left <= 5:
            if int(self.time_left * 10) % 2 == 0:
                warn = font.render("HURRY!", True, YELLOW)
                surf.blit(warn, (WIDTH//2 - warn.get_width()//2, 48))

        # debug miss-heat
        if self.debug:
            heat = self.spawner.miss_heat
            dbg = font.render(f"MissHeat: +{int(100*heat)}%", True, YELLOW)
            surf.blit(dbg, (16, 48))

        # tips
        tips = font.render("Click BAD (red) to shutdown • F1 debug • R reset", True, GRAY)
        surf.blit(tips, (16, HEIGHT - 32))

    def draw(self, surf):
        surf.fill((28, 34, 42))
        self.draw_conveyor(surf)
        for r in self.robots:
            r.draw(surf, debug=self.debug, pulse=self.pulse)

        self.draw_hud(surf)

        if self.game_over:
            msg = "YOU WIN!" if self.win else "GAME OVER"
            label = big_font.render(msg, True, WHITE)
            sub = font.render("Left-click to continue", True, CREAM)
            surf.blit(label, (WIDTH//2 - label.get_width()//2, HEIGHT//2 - 40))
            surf.blit(sub, (WIDTH//2 - sub.get_width()//2, HEIGHT//2 + 10))

def main():
    random.seed()
    game = Game(level_index=0)

    while True:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit(0)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F1:
                    game.debug = not game.debug
                elif event.key == pygame.K_r:
                    game.reset()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = pygame.mouse.get_pos()
                if game.game_over:
                    # click tiếp màn hoặc reset (màn cuối quay về L1)
                    if game.win:
                        game.next_level()
                    else:
                        game.reset()
                else:
                    game.handle_click(mx, my)

        game.update(dt)
        game.draw(screen)
        pygame.display.flip()

if __name__ == "__main__":
    main()
