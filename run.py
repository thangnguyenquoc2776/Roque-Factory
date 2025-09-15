import os, sys
import pygame

BASE_DIR = os.path.dirname(__file__)
SRC_DIR = os.path.join(BASE_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

from engine.app import GameApp

def main():
    app = GameApp(base_dir=BASE_DIR)
    app.run()

if __name__ == "__main__":
    main()
