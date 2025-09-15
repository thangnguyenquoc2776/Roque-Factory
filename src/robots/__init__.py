from data.registry import register_robot
from .ok import RobotOK
from .bad import RobotBAD
# Giữ lại nếu sau này dùng:
# from .bad_exploder import RobotBadExploder
# from .bad_runner import RobotBadRunner

@register_robot("OK")
class _OK(RobotOK): pass

@register_robot("BAD")
class _B(RobotBAD): pass

# @register_robot("BAD_EXPLODER")
# class _BE(RobotBadExploder): pass
# @register_robot("BAD_RUNNER")
# class _BR(RobotBadRunner): pass
