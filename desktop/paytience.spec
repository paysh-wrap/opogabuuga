# PyInstaller spec — builds Paytience (one folder, console window) with backend, rules, alembic and built UI inside.
from PyInstaller.utils.hooks import collect_submodules, collect_data_files
from pathlib import Path
ROOT = Path(SPECPATH).parent
datas = [
    (str(ROOT / "frontend" / "dist"), "frontend/dist"),
    (str(ROOT / "config"), "config"),
    (str(ROOT / "backend" / "alembic"), "backend/alembic"),
    (str(ROOT / "backend" / "alembic.ini"), "backend"),
    (str(ROOT / "backend" / "app"), "backend/app"),
    (str(ROOT / "pine"), "pine"),
]
if (ROOT / "desktop" / "version.json").exists():  # D88: written by the workflow (commit SHA + build time)
    datas.append((str(ROOT / "desktop" / "version.json"), "desktop"))
datas += collect_data_files("argon2") + collect_data_files("alembic")
hidden = collect_submodules("app") + collect_submodules("uvicorn") + collect_submodules("sqlalchemy.dialects.sqlite") + ["alembic.command"]
a = Analysis([str(ROOT / "desktop" / "paytience_app.py")], pathex=[str(ROOT / "backend")], datas=datas, hiddenimports=hidden)
pyz = PYZ(a.pure)
icon = str(ROOT / "desktop" / "paytience.ico") if (ROOT / "desktop" / "paytience.ico").exists() else None
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="Paytience", console=True, icon=icon)
coll = COLLECT(exe, a.binaries, a.datas, name="Paytience")
