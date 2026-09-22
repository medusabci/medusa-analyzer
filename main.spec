# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


app_icon = "medusa_analyzer/frontend/styles/medusa_task_icon.png"
splash_image = "medusa_analyzer/frontend/styles/medusa_splash_v2026 copia.png"


data_patterns = [
    "**/*.json",
    "**/*.tsv",
    "**/*.png",
    "**/*.svg",
    "**/*.ico",
    "**/*.qss",
    "**/*.xpm",
    "**/*.ttf",
    "**/*.otf",
]

# Include all package data files while preserving their package structure.
datas = (
    collect_data_files("medusa_analyzer")
    + collect_data_files("medusa")
    + collect_data_files("medusa_style")
)


# Include all package submodules.
hiddenimports = (
    collect_submodules("medusa_analyzer")
    + collect_submodules("medusa_style")
)


a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

# 1. Instanciar el objeto Splash
splash = Splash(
    splash_image,
    binaries=a.binaries,
    datas=a.datas,
    text_pos=None,
    text_size=12,
    minify_script=True
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    splash,              # Referencia al objeto Splash instanciado previamente
    splash.binaries,     # Referencia a los binarios requeridos por Splash
    [],
    name="MedusaAnalyzer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=app_icon
)
