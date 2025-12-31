# ========================
# Configuration
# ========================
PYTHON=python3
VENV=venv
PIP=$(VENV)/bin/pip
PY=$(VENV)/bin/python
APP=app.py
DIST=dist
BUILD=build
SPEC=app.spec

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
	--name=gestion_fertilisants \
	$(APP)

clean:
	rm -rf $(BUILD) $(DIST) __pycache__

reset: clean
	rm -rf $(VENV)
