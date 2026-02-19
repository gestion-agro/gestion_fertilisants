import os
import stat
import sys
from pathlib import Path

def fix_cbc_permissions():
    """
    Rend exécutable le solver CBC embarqué par PyInstaller.
    Nécessaire sur Linux en AppImage / .deb.
    """
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        return  # en dev pas besoin

    cbc_path = base / "pulp" / "solverdir" / "cbc" / "linux" / "i64" / "cbc"

    if cbc_path.exists():
        try:
            st = os.stat(cbc_path)
            os.chmod(cbc_path, st.st_mode | stat.S_IEXEC)
        except Exception as e:
            print("Erreur permission CBC:", e)
