from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any

FPoint = Tuple[float, float]

@dataclass
class StationSpec:
    pos: FPoint
    id: str = ""

@dataclass
class MapStationsCfg:
    preset: str = ""
    points: List[FPoint] = field(default_factory=list)
    add_points: List[FPoint] = field(default_factory=list)
    remove_indices: List[int] = field(default_factory=list)
    generator: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PathSpec:
    points: List[FPoint]

@dataclass
class MapSpec:
    map_id: str
    name: str
    background: str = ""
    conveyor: Dict[str, Any] = field(default_factory=dict)
    decor: Dict[str, Any] = field(default_factory=dict)
    paths: List[PathSpec] = field(default_factory=list)
    stations_cfg: MapStationsCfg = field(default_factory=MapStationsCfg)

@dataclass
class RobotDef:
    type: str
    weight: float = 1.0
    params: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SpawnSpec:
    interval: float
    robots: List[RobotDef] = field(default_factory=list)

@dataclass
class LevelSpec:
    level_id: str
    name: str
    map: str
    time: int
    goal: int
    spawn: SpawnSpec
