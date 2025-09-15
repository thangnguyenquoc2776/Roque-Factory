import pygame
from engine.state import State

class LevelSelectState(State):
    def enter(self, **kwargs):
        self.levels = self.app.levels
        self.sel = 0

    def handle_event(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_UP, pygame.K_w):
                self.sel = (self.sel - 1) % len(self.levels)
            elif e.key in (pygame.K_DOWN, pygame.K_s):
                self.sel = (self.sel + 1) % len(self.levels)
            elif e.key in (pygame.K_RETURN, pygame.K_SPACE):
                # lazy import ngay khi cần chuyển state
                from .gameplay import GameplayState
                self.app.switch_state(GameplayState(self.app), level_index=self.sel)
            elif e.key == pygame.K_ESCAPE:
                from .main_menu import MainMenuState
                self.app.switch_state(MainMenuState(self.app))

    def update(self, dt):
        pass

    def draw(self, screen):
        screen.fill((24,28,34))
        title = self.app.big_font.render("Select Level", True, (244,244,236))
        screen.blit(title, (screen.get_width()//2 - title.get_width()//2, 80))
        for i,lv in enumerate(self.levels):
            color = (243,198,62) if i==self.sel else (200,205,210)
            text = self.app.font.render(f"{lv.level_id} - {lv.name}", True, color)
            screen.blit(text, (screen.get_width()//2 - text.get_width()//2, 180 + i*32))
