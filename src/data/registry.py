ROBOT_TYPES = {}

def register_robot(name):
    def deco(cls):
        ROBOT_TYPES[name.upper()] = cls
        return cls
    return deco
