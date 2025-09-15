import os, glob, yaml
from typing import Dict, Any, List
from .schema import (
    MapSpec, MapStationsCfg, PathSpec,
    LevelSpec, SpawnSpec, RobotDef
)
from src.engine.geometry import rescale_points, project_point_to_t, sample_path_t

def _read_yaml(path: str, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or (default or {})
    except Exception:
        return default or {}

class Loader:
    """
    Đọc toàn bộ config của game:
      - Game config            -> configs/game.yaml
      - Station presets        -> configs/presets/stations/*.yaml
      - Maps                   -> configs/maps/*.yaml  (tham chiếu presets)
      - Levels                 -> configs/levels/*.yaml
      - I18N (ngôn ngữ)        -> configs/i18n/<lang>.yaml (+ merge với default)
    Ngoài ra cung cấp resolve_stations_for_path() để chuyển station 0..1 -> pixel & t.
    """
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.config_dir = os.path.join(base_dir, "configs")
        self._station_presets: Dict[str, List[List[float]]] = None

    # ---------- Game config ----------
    def load_game_config(self) -> Dict[str, Any]:
        return _read_yaml(os.path.join(self.config_dir, "game.yaml"), default={
            "game": {"title": "Rogue Factory", "resolution": [1280, 720], "target_fps": 60},
            "defaults": {"hp": 3, "robot_speed": 0.12},
            "language": {"default": "vi", "available": ["vi", "en"]}
        })

    # ---------- Station presets ----------
    def load_station_presets(self) -> Dict[str, List[List[float]]]:
        if self._station_presets is not None:
            return self._station_presets
        presets_dir = os.path.join(self.config_dir, "presets", "stations")
        presets: Dict[str, List[List[float]]] = {}
        if os.path.isdir(presets_dir):
            for f in glob.glob(os.path.join(presets_dir, "*.yaml")):
                d = _read_yaml(f, default={})
                pid = d.get("preset_id")
                pts = d.get("points", [])
                if pid and pts:
                    presets[pid] = pts  # list of [x, y] (0..1)
        self._station_presets = presets
        return presets

    # ---------- Maps ----------
    def load_maps(self) -> Dict[str, MapSpec]:
        _ = self.load_station_presets()  # đảm bảo đã cache preset
        maps: Dict[str, MapSpec] = {}
        maps_dir = os.path.join(self.config_dir, "maps")
        if os.path.isdir(maps_dir):
            for f in glob.glob(os.path.join(maps_dir, "*.yaml")):
                d = _read_yaml(f, default={})
                if not d:
                    continue
                scfg = d.get("stations", {})
                stations_cfg = MapStationsCfg(
                    preset = scfg.get("preset",""),
                    points = scfg.get("points",[]) or [],
                    add_points = scfg.get("add_points",[]) or [],
                    remove_indices = scfg.get("remove_indices",[]) or [],
                    generator = scfg.get("generator",{}) or {},
                )
                m = MapSpec(
                    map_id=d.get("map_id","unknown"),
                    name=d.get("name","Unnamed"),
                    background=d.get("background",""),
                    conveyor=d.get("conveyor",{}),
                    decor=d.get("decor",{}),
                    paths=[PathSpec(points=p.get("points",[])) for p in d.get("paths",[])],
                    stations_cfg=stations_cfg,
                )
                maps[m.map_id] = m

        # fallback nếu không có file map nào
        if not maps:
            maps["straight"] = MapSpec(
                map_id="straight", name="Straight Line",
                paths=[PathSpec(points=[(0.08,0.5),(0.92,0.5)])],
                stations_cfg=MapStationsCfg(preset="straight_default")
            )
        return maps

    def resolve_stations_for_path(self, map_spec, path_idx, screen_size):
        W, H = screen_size
        path_norm = map_spec.paths[path_idx].points
        path_px = rescale_points(path_norm, W, H)

        pts = []
        scfg = map_spec.stations_cfg
        if scfg.preset:
            pts.extend(self.load_station_presets().get(scfg.preset, []))
        if scfg.points:
            pts.extend(scfg.points)
        if scfg.add_points:
            pts.extend(scfg.add_points)
        if scfg.remove_indices:
            keep = [i for i in range(len(pts)) if i not in set(scfg.remove_indices)]
            pts = [pts[i] for i in keep]

        station_ts = []
        for (nx, ny) in pts:
            px, py = int(nx * W), int(ny * H)
            t = project_point_to_t(path_px, px, py)
            station_ts.append(round(t, 4))  # tránh sai số cộng dồn

        return {"ts": station_ts}

    # ---------- Levels ----------
    def load_levels(self) -> List[LevelSpec]:
        """Đọc tất cả các file levels trong configs/levels/*.yaml"""
        levels: List[LevelSpec] = []
        levels_dir = os.path.join(self.config_dir, "levels")
        if os.path.isdir(levels_dir):
            for f in glob.glob(os.path.join(levels_dir, "*.yaml")):
                data = _read_yaml(f, default={})
                for lvl in data.get("levels", []):
                    # Chuẩn hoá spawn->robots vào dataclass
                    spawn = lvl.get("spawn", {})
                    robots = []
                    for r in spawn.get("robots", []):
                        if isinstance(r, dict):
                            rtype = r.get("type")
                            weight = float(r.get("weight", 1.0))
                            params = dict(r); params.pop("type", None); params.pop("weight", None)
                            robots.append(RobotDef(type=rtype, weight=weight, params=params))
                    spawn_spec = SpawnSpec(interval=float(spawn.get("interval", 1.5)), robots=robots)
                    levels.append(LevelSpec(
                        level_id=lvl.get("level_id",""),
                        name=lvl.get("name",""),
                        map=lvl.get("map","straight"),
                        time=int(lvl.get("time", 120)),
                        goal=int(lvl.get("goal", 20)),
                        spawn=spawn_spec
                    ))
        # fallback nếu rỗng
        if not levels:
            levels.append(LevelSpec(
                level_id="L1",
                name="Level 1 — Straight",
                map="straight",
                time=120,
                goal=20,
                spawn=SpawnSpec(interval=1.6, robots=[RobotDef(type="OK", weight=1.0, params={})])
            ))
        return levels

    # ---------- I18N ----------
    def load_i18n(self, lang_code: str) -> Dict[str, Any]:
        """
        Hợp nhất i18n theo thứ tự ưu tiên:
          default.yaml (nếu có)  -> en.yaml (nếu lang=en)  -> <lang_code>.yaml
        Cái nào đến sau sẽ ghi đè khoá cùng tên.
        """
        i18n_dir = os.path.join(self.config_dir, "i18n")
        out: Dict[str, Any] = {}

        def merge_into(target: Dict[str, Any], src: Dict[str, Any]):
            for k, v in (src or {}).items():
                if isinstance(v, dict) and isinstance(target.get(k), dict):
                    merge_into(target[k], v)
                else:
                    target[k] = v

        # 1) default
        default_path = os.path.join(i18n_dir, "default.yaml")
        merge_into(out, _read_yaml(default_path, default={}))

        # 2) en (nếu được gọi là en)
        if lang_code == "en":
            merge_into(out, _read_yaml(os.path.join(i18n_dir, "en.yaml"), default={}))

        # 3) lang cụ thể
        merge_into(out, _read_yaml(os.path.join(i18n_dir, f"{lang_code}.yaml"), default={}))

        return out
