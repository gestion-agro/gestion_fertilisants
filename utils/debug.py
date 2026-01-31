# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

# utils/debug.py

DEBUG = True

def debug(*args):
    if DEBUG:
        print(*args)