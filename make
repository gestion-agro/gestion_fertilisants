Licensed under PolyForm Noncommercial 1.0.0
© 2026 Clément THIEULEUX

python -m venv venv
venv\Scripts\activate
pip install pyside6 scipy numpy pyinstaller
pyinstaller --onefile --windowed --icon=icon.ico --add-data "icon.ico:." --add-data "data;data" --clean app.py

