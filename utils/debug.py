# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

# utils/debug.py

# False = Pas débug
# True = Débug
DEBUG = True

def set_debug(value: bool):
    global DEBUG
    DEBUG = value

def toggle_debug():
    global DEBUG
    DEBUG = not DEBUG
    return DEBUG

def is_debug():
    return DEBUG

def debug(*args):
    if DEBUG:
        print(*args)