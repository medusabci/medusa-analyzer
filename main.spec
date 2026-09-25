# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


app_icon = "medusa_analyzer/frontend/styles/medusa_task_icon.png"


test_path_markers = (
    "/tests/",
    "\\tests\\",
)

excluded_modules = [
    "h5py.tests",
    "medusa_analyzer.frontend.splash",
    "numpy._pytesttester",
    "numpy.testing",
    "pandas._testing",
    "pandas.testing",
    "pandas.util._tester",
    "patsy.test_splines_bs_data",
    "patsy.test_splines_crs_data",
    "patsy.test_state",
    "pytest",
    "pyparsing.testing",
    "pywt._pytesttester",
    "scipy._lib._testutils",
    "sklearn.utils._testing",
    "statsmodels.tools._test_runner",
]

startup_artifact_markers = (
    "medusa_analyzer/frontend/splash.py",
    "medusa_analyzer\\frontend\\splash.py",
    "medusa_analyzer/frontend/styles/medusa_splash",
    "medusa_analyzer\\frontend\\styles\\medusa_splash",
    "medusa_analyzer/frontend/styles/splash.png",
    "medusa_analyzer\\frontend\\styles\\splash.png",
)


def without_test_artifacts(items):
    return [
        item
        for item in items
        if not any(marker in str(part).lower() for marker in test_path_markers for part in item[:2])
    ]


def without_startup_artifacts(items):
    return [
        item
        for item in items
        if not any(marker in str(part).lower() for marker in startup_artifact_markers for part in item[:2])
    ]


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
datas = without_startup_artifacts(without_test_artifacts(datas))


# Include all package submodules.
hiddenimports = (
    collect_submodules("medusa_analyzer")
    + collect_submodules("medusa_style")
)
hiddenimports = [
    module for module in hiddenimports
    if module not in excluded_modules
]


a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excluded_modules,
    noarchive=False,
    optimize=0,
)
a.datas = without_startup_artifacts(without_test_artifacts(a.datas))

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
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
