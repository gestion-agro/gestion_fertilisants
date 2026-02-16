# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

# ========================
# Configuration
# ========================
ifeq ($(OS),Windows_NT)
	PYTHON=python
	VENV=venv
	VENV_BIN=$(VENV)/Scripts
	PY=$(VENV_BIN)/python
	PIP=$(VENV_BIN)/pip
	PYINSTALLER=$(VENV_BIN)/pyinstaller
	RM=rd /s /q
else
	PYTHON=python3
	VENV=venv
	VENV_BIN=$(VENV)/bin
	PY=$(VENV_BIN)/python
	PIP=$(VENV_BIN)/pip
	PYINSTALLER=$(VENV_BIN)/pyinstaller
	RM=rm -rf
endif

APP=app.py
DIST=dist
BUILD=build
RELEASEs=releases
DOWNLOAD=download
NAME=gestion_fertilisants
ICON=icon.ico

	

# ========================
# Règles
# ========================

.PHONY: help venv install run build clean reset

help:
	@echo "Commandes disponibles :"
	@echo "  make venv      -> créer l'environnement virtuel"
	@echo "  make install   -> installer les dépendances"
	@echo "  make run       -> lancer l'application"
	@echo "  make build     -> générer l'exécutable"
	@echo "  make clean     -> nettoyer les fichiers générés"
	@echo "  make reset     -> clean + suppression venv"

venv:
	$(PYTHON) -m venv $(VENV)

install: venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

run:
	$(PY) $(APP)

build:
	$(VENV)/bin/pyinstaller \
	--onefile \
	--windowed \
	--icon=icon.ico \
	--name=$(NAME) \
	$(APP)

releases: build
	@echo "Préparation des dossiers de releases..."
	mkdir -p $(DOWNLOAD)
	@echo "Copie du binaire vers $(DOWNLOAD)..."
	cp $(BUILD)/$(NAME) $(DOWNLOAD)/$(NAME)
	@echo "Release prête"

clean:
	rm -rf $(BUILD) $(DIST) __pycache__

reset: clean
	rm -rf $(VENV)
