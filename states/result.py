import pygame
from engine.state import State
from engine.render import draw_hud

# ...existing code...
import pygame
from engine.state import State
from engine.render import draw_hud

class ResultState(State):
    def enter(self, **kwargs):
        # win flag / main message
        self.win = kwargs.get("win", False)
        self.msg = "YOU WIN!" if self.win else "GAME OVER"

        # stats to show in HUD (passed from GameplayState.some_end_game_path)
        self.stats = kwargs.get("stats", {}) or {}

        # ensure we have reference to app (State usually sets this, but allow override)
        if "app" in kwargs and kwargs["app"] is not None:
            self.app = kwargs["app"]

    def handle_event(self, e):
        if e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
            from .level_select import LevelSelectState  # lazy import
            self.app.switch_state(LevelSelectState(self.app))

    def update(self, dt):
        pass

        # ...existing code...
    def draw(self, screen):
        # background
        screen.fill((28, 34, 42))

        # draw HUD overlay nếu có
        try:
            draw_hud(screen, self.stats)
        except Exception:
            pass

        # Title
        big_font = getattr(self.app, "big_font", None) or getattr(self.app, "font", None)
        small_font = getattr(self.app, "font", None)

        title_y = 120
        if big_font:
            label = big_font.render(self.msg, True, (244, 244, 236))
            screen.blit(label, (screen.get_width() // 2 - label.get_width() // 2, title_y))
            title_y += label.get_height() + 12

        # Render stats block centered dưới title
        if small_font and self.stats:
            lines = []
            order = ("production", "goal", "hits", "misses", "accuracy", "time_left", "HP", "score")
            for k in order:
                if k in self.stats:
                    v = self.stats[k]
                    if k == "accuracy":
                        try:
                            v = f"{float(v):.1%}"
                        except Exception:
                            pass
                    elif k == "time_left":
                        try:
                            v = f"{float(v):.1f}s"
                        except Exception:
                            pass
                    # giữ nguyên chữ HP in hoa
                    if k.upper() == "HP":
                        name = "HP"
                    else:
                        name = k.replace("_", " ").title()
                    lines.append((name, str(v)))
            # thêm các key khác nếu có
            for k, v in self.stats.items():
                if k not in order:
                    name = "HP" if k.upper() == "HP" else k.replace("_", " ").title()
                    lines.append((name, str(v)))

            # tính width để căn cột
            name_widths = [small_font.size(n + ":")[0] for n, _ in lines] or [0]
            val_widths = [small_font.size(v)[0] for _, v in lines] or [0]
            name_max = max(name_widths)
            val_max = max(val_widths)

            padding = 24
            total_w = name_max + padding + val_max
            center_x = screen.get_width() // 2
            col_left = center_x - total_w // 2
            col_right = col_left + total_w

            # đẩy block thống kê xuống thêm 20px để tránh dính sát title
            y = title_y + 20
            for name, val in lines:
                name_surf = small_font.render(f"{name}:", True, (220, 220, 220))
                val_surf = small_font.render(val, True, (220, 220, 220))
                screen.blit(name_surf, (col_left, y))
                screen.blit(val_surf, (col_right - val_surf.get_width(), y))
                y += name_surf.get_height() + 6

        # Subtext ở cuối màn hình
        if small_font:
            sub = small_font.render("Press Enter to continue", True, (200, 205, 210))
            bottom_y = screen.get_height() - 48
            screen.blit(sub, (screen.get_width() // 2 - sub.get_width() // 2, bottom_y))

