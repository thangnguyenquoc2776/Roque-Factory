from typing import Any

class State:
    def __init__(self, app):
        self.app = app
    def enter(self, **kwargs): pass
    def handle_event(self, e): pass
    def update(self, dt: float): pass
    def draw(self, screen): pass
    def exit(self): pass
