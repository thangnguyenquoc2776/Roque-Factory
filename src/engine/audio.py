import pygame

class Audio:
    def __init__(self, sfx_map=None, music_volume=0.8):
        self.sfx = {}
        self.music_volume = music_volume
        if sfx_map:
            for k, path in sfx_map.items():
                try:
                    self.sfx[k] = pygame.mixer.Sound(path)
                except Exception:
                    self.sfx[k] = None
        try:
            pygame.mixer.music.set_volume(music_volume)
        except Exception:
            pass

    def play_sfx(self, key):
        snd = self.sfx.get(key)
        if snd:
            try: snd.play()
            except Exception: pass

    def play_music(self, path, loop=True):
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.play(-1 if loop else 0)
        except Exception:
            pass
