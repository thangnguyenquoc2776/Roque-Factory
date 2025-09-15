import glob
import os, pygame

from engine.audio import Audio
from .state import State
from data.loader import Loader
from states.boot import BootState

class GameApp:
    def __init__(self, base_dir):
        pygame.init()
        self.base_dir = base_dir
        self.loader = Loader(base_dir)
        self.config = self.loader.load_game_config()

        ##! INIT AUDIO
        sfx_dir = os.path.join(base_dir, "assets", "sounds", "SFX")
        sfx_map = {}
        if os.path.isdir(sfx_dir):
            for f in glob.glob(os.path.join(sfx_dir, "*")):
                if os.path.isfile(f):
                   key = os.path.splitext(os.path.basename(f))[0].upper()
                   sfx_map[key] = f
        #!VOLUME
        music_vol = float(self.config.get("audio", {}).get("music_volume", 0.1))
        try:
            self.audio = Audio(sfx_map=sfx_map, music_volume=music_vol)
        except Exception:
            self.audio = None

        W, H = self.config.get("game", {}).get("resolution", [1280, 720])
        self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption(self.config.get("game", {}).get("title", "Rogue Factory"))

        self.clock = pygame.time.Clock()
        self.fps = self.config.get("game", {}).get("target_fps", 60)
        self.font = pygame.font.SysFont("arialrounded", 24)
        self.big_font = pygame.font.SysFont("arialrounded", 48)


        #! --- LOAD SPRITES / APPLY CONFIGURED SCALES ---
        self.sprites = {}
        sprites_cfg = self.config.get("sprites", {})  # expected keys uppercase -> value: float(scale) or [w,h]
        sprites_root = os.path.join(base_dir, "assets", "images", "robot")
        def _load(p):
            try:
                return pygame.image.load(p).convert_alpha()
            except Exception:
                return None

        def _apply_scale(img, scale_val):
            if img is None or scale_val is None:
                return img
            try:
                if isinstance(scale_val, (int, float)):
                    w = max(1, int(img.get_width() * float(scale_val)))
                    h = max(1, int(img.get_height() * float(scale_val)))
                elif isinstance(scale_val, (list, tuple)) and len(scale_val) == 2:
                    w = int(scale_val[0]); h = int(scale_val[1])
                else:
                    return img
                return pygame.transform.smoothscale(img, (w, h))
            except Exception:
                return img

        if os.path.isdir(sprites_root):
            ok_path = os.path.join(sprites_root, "anim0a.png")
            if os.path.isfile(ok_path):
                img = _load(ok_path)
                if img:
                    key = "OK"
                    img = _apply_scale(img, sprites_cfg.get(key))
                    self.sprites[key] = [img]

            bad_trans_paths = [os.path.join(sprites_root, n) for n in ("anim2.png", "anim3.png", "anim4.png")]
            bad_trans = []
            for p in bad_trans_paths:
                if os.path.isfile(p):
                    img = _load(p)
                    if img:
                        # apply same scale for BAD_TRANS if configured under BAD_TRANS else BAD_LOOP else None
                        img = _apply_scale(img, sprites_cfg.get("BAD_TRANS") or sprites_cfg.get("BAD_LOOP"))
                        bad_trans.append(img)
            bad_trans = [f for f in bad_trans if f]
            if bad_trans:
                self.sprites["BAD_TRANS"] = bad_trans

            bad_loop_paths = [os.path.join(sprites_root, n) for n in ("anim3.png", "anim4.png")]
            bad_loop = []
            for p in bad_loop_paths:
                if os.path.isfile(p):
                    img = _load(p)
                    if img:
                        img = _apply_scale(img, sprites_cfg.get("BAD_LOOP"))
                        bad_loop.append(img)
            bad_loop = [f for f in bad_loop if f]
            if bad_loop:
                self.sprites["BAD_LOOP"] = bad_loop

        #LOAD VFX
        vfx_cfg = self.config.get("vfx", {}) or {}
        self.vfx = {}
        vfx_root = os.path.join(base_dir, "assets", "images", "VFX")
        def _load(p):
            try:
                return pygame.image.load(p).convert_alpha()
            except Exception:
                return None
        def _apply_scale(img, scale_val):
            if img is None or scale_val is None:
                return img
            try:
                if isinstance(scale_val, (int, float)):
                    w = max(1, int(img.get_width() * float(scale_val)))
                    h = max(1, int(img.get_height() * float(scale_val)))
                elif isinstance(scale_val, (list, tuple)) and len(scale_val) == 2:
                    w = int(scale_val[0]); h = int(scale_val[1])
                else:
                    return img
                return pygame.transform.smoothscale(img, (w, h))
            except Exception:
                return img

        if os.path.isdir(vfx_root):
            import re
            files = sorted([f for f in glob.glob(os.path.join(vfx_root, "*")) if os.path.isfile(f)])
            groups = {}
            for f in files:
                name = os.path.splitext(os.path.basename(f))[0]
                m = re.match(r"^([A-Za-z0-9]+?)(?:[_\-](\d+))?$", name)
                base = (m.group(1) if m else name).upper()
                idx = int(m.group(2)) if (m and m.group(2)) else 0
                groups.setdefault(base, []).append((idx, f))
            for key, items in groups.items():
                items.sort(key=lambda x: x[0])
                frames = []
                scale_val = vfx_cfg.get(key)
                for _, path in items:
                    img = _load(path)
                    if not img: continue
                    img = _apply_scale(img, scale_val)
                    frames.append(img)
                if frames:
                    self.vfx[key] = frames

        self.state_stack = []
        self.running = True

        # Push Boot state
        self.push_state(BootState(self))

    def push_state(self, st: State, **kwargs):
        self.state_stack.append(st)
        st.enter(**kwargs)

    def pop_state(self):
        if self.state_stack:
            top = self.state_stack.pop()
            top.exit()

    def switch_state(self, st: State, **kwargs):
        self.pop_state()
        self.push_state(st, **kwargs)

    def current_state(self):
        return self.state_stack[-1] if self.state_stack else None

    def run(self):
        while self.running and self.current_state():
            dt = self.clock.tick(self.fps) / 1000.0
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.running = False
                else:
                    self.current_state().handle_event(e)
            self.current_state().update(dt)
            self.current_state().draw(self.screen)
            pygame.display.flip()
        pygame.quit()
