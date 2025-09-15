import pygame
from typing import Tuple, List
from .geometry import sample_path_t

CREAM = (244, 244, 236)
UI_BG = (18, 22, 26)
YELLOW = (243, 198, 62)
BLACK = (0, 0, 0)
STEEL = (60, 80, 100)
GRAY = (90, 99, 110)
GREEN = (80, 180, 120)


def draw_conveyor(surf, path_pts: List[Tuple[int, int]], width=24):
    if len(path_pts) < 2: return
    pygame.draw.lines(surf, STEEL, False, path_pts, width)
    pygame.draw.lines(surf, BLACK, False, path_pts, 2)


def draw_stations(surf, path_pts: List[Tuple[int, int]], station_ts: List[float]):
    # Vẽ trạm theo cùng 1 nguồn dữ liệu: ts
    for t in station_ts:
        x, y = sample_path_t(path_pts, t)
        pygame.draw.circle(surf, GREEN, (x, y), 8)
        pygame.draw.circle(surf, BLACK, (x, y), 8, 2)


def draw_hud(surf, font, time_left, production, goal, hp, acc, hits, misses):
    W, H = surf.get_size()
    pygame.draw.rect(surf, UI_BG, (0, 0, W, 48))

    # Các text
    t_text = font.render(f"Time: {max(0, int(time_left))}s", True, CREAM)
    pg_text = font.render(f"Production: {production}/{goal}", True, CREAM)
    hp_text = font.render(f"HP: {hp}", True, CREAM)
    hit_text = font.render(f"Hits: {hits}", True, CREAM)
    miss_text = font.render(f"Misses: {misses}", True, CREAM)
    acc_text = font.render(f"Acc: {acc:.0f}%", True, CREAM)

    # Căn vị trí
    surf.blit(t_text, (16, 12))
    surf.blit(pg_text, (W // 2 - pg_text.get_width() // 2, 12))

    rx = W - 16
    surf.blit(acc_text, (rx - acc_text.get_width(), 12));
    rx -= acc_text.get_width() + 16
    surf.blit(miss_text, (rx - miss_text.get_width(), 12));
    rx -= miss_text.get_width() + 16
    surf.blit(hit_text, (rx - hit_text.get_width(), 12));
    rx -= hit_text.get_width() + 16
    surf.blit(hp_text, (rx - hp_text.get_width(), 12))

    # Cảnh báo khi sắp hết giờ
    if 0 < time_left <= 5 and int(time_left * 10) % 2 == 0:
        warn = font.render("HURRY!", True, YELLOW)
        surf.blit(warn, (W // 2 - warn.get_width() // 2, 48))
