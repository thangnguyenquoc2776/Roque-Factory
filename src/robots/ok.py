import random
from .base import RobotBase
from data.registry import ROBOT_TYPES

class RobotOK(RobotBase):
    def __init__(self, *args, fail_prob: float=0.0, fail_probs=None, variants=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fail_prob = float(fail_prob)
        self.fail_probs = list(fail_probs) if fail_probs is not None else None
        self.variants = list(variants) if variants else []

    def _choose_variant(self):
        if not self.variants:
            return None, {}
        total = sum(float(v.get("weight",1.0)) for v in self.variants) or 1.0
        r = random.random() * total
        acc = 0.0
        for v in self.variants:
            acc += float(v.get("weight",1.0))
            if r <= acc:
                t = v.get("type","").upper()
                params = dict(v.get("params",{}))
                cls = ROBOT_TYPES.get(t)
                if cls: return cls, params
        v = self.variants[-1]
        return ROBOT_TYPES.get(v.get("type","").upper()), dict(v.get("params",{}))

    def on_reach_station(self, station_idx: int):
        # Xác suất lỗi tại trạm
        p = (float(self.fail_probs[station_idx])
             if (self.fail_probs is not None and station_idx < len(self.fail_probs))
             else self.fail_prob)
        if p <= 0:
            return
        if random.random() < p:
            cls, params = self._choose_variant()
            if cls is not None:
                # Thay thế tại chỗ: robot cũ chết, robot mới kế tục đủ trạng thái
                self.mutate_to(cls, **params)
