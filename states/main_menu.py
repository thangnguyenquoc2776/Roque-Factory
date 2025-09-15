import pygame
from engine.state import State

class MainMenuState(State):
    def enter(self, **kwargs):
        self.items = [("PLAY", self.play), ("QUIT", self.quit)]
        self.sel = 0

    def play(self):
        # lazy import để tránh vòng lặp
        from .level_select import LevelSelectState
        self.app.switch_state(LevelSelectState(self.app))

    def quit(self):
        self.app.running = False

    def handle_event(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_UP, pygame.K_w):
                self.sel = (self.sel - 1) % len(self.items)
            elif e.key in (pygame.K_DOWN, pygame.K_s):
                self.sel = (self.sel + 1) % len(self.items)
            elif e.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.items[self.sel][1]()

    def update(self, dt):
        pass

    def draw(self, screen):
        screen.fill((18,22,26))
        title = self.app.big_font.render("Rogue Factory", True, (244,244,236))
        screen.blit(title, (screen.get_width()//2 - title.get_width()//2, 100))
        for i,(label,_) in enumerate(self.items):
            color = (243,198,62) if i==self.sel else (200,205,210)
            text = self.app.font.render(label, True, color)
            screen.blit(text, (screen.get_width()//2 - text.get_width()//2, 220 + i*40))
