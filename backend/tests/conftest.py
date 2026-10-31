import os
import sys
import tempfile
from pathlib import Path

# Les tests importent le paquet `app` depuis backend/ et n'écrivent jamais dans la vraie sauvegarde.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("GMIX_DB_PATH", str(Path(tempfile.mkdtemp()) / "gmix.db"))
