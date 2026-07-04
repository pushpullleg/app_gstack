# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — onefile, windowed, icon=packaging/app.ico
# Build ONLY on windows-latest CI; PyInstaller cannot cross-compile.
#
# Usage (from repo root):
#   pyinstaller packaging/activity_logger.spec
#
# Or via:
#   scripts/build_windows.ps1

from pathlib import Path

block_cipher = None

# Exclude heavy Qt subsystems we don't use.
EXCLUDES = [
    "QtWebEngineCore",
    "QtWebEngine",
    "QtWebEngineWidgets",
    "QtQml",
    "QtQuick",
    "Qt3DCore",
    "Qt3DRender",
    "Qt3DInput",
    "Qt3DLogic",
    "Qt3DExtras",
    "Qt3DAnimation",
    "QtCharts",
    "QtMultimedia",
    "QtMultimediaWidgets",
    "QtNetwork",
    "QtBluetooth",
    "QtNfc",
    "QtSensors",
    "QtPositioning",
    "QtLocation",
    "QtRemoteObjects",
    "QtSql",
    "QtTest",
    "QtXml",
]

a = Analysis(
    ["../src/activity_logger/__main__.py"],
    pathex=["../src"],
    binaries=[],
    datas=[],
    hiddenimports=[
        "activity_logger",
        "activity_logger.app",
        "activity_logger.config",
        "activity_logger.db.connection",
        "activity_logger.db.migrations",
        "activity_logger.db.seed",
        "activity_logger.models.entities",
        "activity_logger.repositories.departments",
        "activity_logger.repositories.activity_codes",
        "activity_logger.repositories.employees",
        "activity_logger.repositories.log_entries",
        "activity_logger.repositories.generated_reports",
        "activity_logger.services.validation",
        "activity_logger.services.logging_service",
        "activity_logger.services.aggregation_service",
        "activity_logger.services.periods",
        "activity_logger.services.csv_io",
        "activity_logger.services.report_service",
        "activity_logger.reports.federal_report",
        "activity_logger.reports.styles",
        "activity_logger.ui.main_window",
        "activity_logger.ui.views.entry_view",
        "activity_logger.ui.views.monthly_view",
        "activity_logger.ui.views.quarterly_view",
        "activity_logger.ui.models_qt.log_table_model",
        "activity_logger.ui.models_qt.aggregate_model",
        "activity_logger.ui.widgets.dept_code_picker",
        # ReportLab Base-14 font data
        "reportlab.graphics",
        "reportlab.platypus",
        "reportlab.lib",
        "reportlab.pdfgen",
        "reportlab.pdfbase",
        "reportlab.rl_config",
    ],
    excludes=EXCLUDES,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="ActivityLogger",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # windowed — no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="app.ico" if Path("app.ico").exists() else None,
)
