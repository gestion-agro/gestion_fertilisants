# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

#! /usr/bin/env bash
#
find . -name "__pycache__" -type d -exec rm -rf {} + && find . -name "*.pyc" -delete && echo "Netoyage effectué"
