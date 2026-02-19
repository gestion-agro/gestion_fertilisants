# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

# utils/debug.py

# False = Pas débug
# True = Débug
DEBUG = False

def debug(*args):
    if DEBUG:
        print(*args)