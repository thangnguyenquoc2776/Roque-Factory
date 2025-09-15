import pygame

def is_accept(e):
    return (e.type==pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_SPACE))

def is_back(e):
    return (e.type==pygame.KEYDOWN and e.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE))

def is_click(e):
    return (e.type==pygame.MOUSEBUTTONDOWN and e.button==1)
