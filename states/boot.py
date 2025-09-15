import glob
import os
from engine.state import State
from .main_menu import MainMenuState

class BootState(State):
    def enter(self, **kwargs):
        # Preload minimal configs (maps, levels, i18n)
        self.app.maps   = self.app.loader.load_maps()
        self.app.levels = self.app.loader.load_levels()
        lang = self.app.config.get("language",{}).get("default","vi")
        self.app.i18n   = self.app.loader.load_i18n(lang)

        # Play background music (first file in assets/sounds/Background if any)
        try:
            if getattr(self.app, "audio", None):
                bg_dir = os.path.join(self.app.base_dir, "assets", "sounds", "Background")
                if os.path.isdir(bg_dir):
                    files = [f for f in glob.glob(os.path.join(bg_dir, "*")) if os.path.isfile(f)]
                    if files:
                        self.app.audio.play_music(files[1], loop=True)
        except Exception:
            pass
        # Go to menu
        self.app.switch_state(MainMenuState(self.app))

    def update(self, dt): pass
    def draw(self, screen):
        screen.fill((20,20,24))
