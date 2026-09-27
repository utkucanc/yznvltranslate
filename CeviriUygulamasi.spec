# -*- mode: python ; coding: utf-8 -*-
# PyInstaller Spec Dosyası - CeviriUygulamasi
# Kullanım:
#   pyinstaller CeviriUygulamasi.spec
#
# Kurulum için önce PyInstaller'ı yükleyin:
#   pip install pyinstaller

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# --- Gizli Import'lar (PyInstaller'ın otomatik bulamadıkları) ---
hiddenimports = [
    # PyQt6
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
    "PyQt6.sip",

    # Proje modülleri - Kök & Core
    "dialogs",
    "logger",
    "sqlite3",
    "core",
    "core.chapter_check_worker",
    "core.database_manager",
    "core.file_list_manager",
    "core.free_translators",
    "core.llm_provider",
    "core.localization",
    "core.merge_controller",
    "core.path_resolver",
    "core.process_controller",
    "core.project_manager",
    "core.startup_worker",
    "core.temizlik",
    "core.theme_defaultCreate",
    "core.theme_engine",
    "core.token_controller",
    "core.translation_controller",
    "core.ui_state_manager",
    "core.utils",

    # Core Workers
    "core.workers",
    "core.workers.cleaning_worker",
    "core.workers.epub_worker",
    "core.workers.jsonoutput",
    "core.workers.local_token_count_worker",
    "core.workers.merging_worker",
    "core.workers.ml_terminology_extractor",
    "core.workers.ml_terminology_worker",
    "core.workers.prompt_generator",
    "core.workers.split_worker",
    "core.workers.text_utils",
    "core.workers.token_count_worker",
    "core.workers.token_counter",
    "core.workers.translation_error_check_worker",
    "core.workers.translation_quality_checker",

    # UI Modülleri
    "ui",
    "ui.api_key_editor_dialog",
    "ui.api_stats_dialog",
    "ui.app_settings_dialog",
    "ui.connection_bar_builder",
    "ui.dark_theme",
    "ui.dashboard_page",
    "ui.file_preview_dialog",
    "ui.file_table_interactions",
    "ui.file_table_manager",
    "ui.free_translators_dialog",
    "ui.gemini_version_dialog",
    "ui.mcp_server_dialog",
    "ui.menu_bar_builder",
    "ui.ml_terminology_range_dialog",
    "ui.new_project_dialog",
    "ui.project_page",
    "ui.project_settings_dialog",
    "ui.prompt_editor_dialog",
    "ui.request_counter_manager",
    "ui.right_panel_builder",
    "ui.sidebar_builder",
    "ui.splash_screen",
    "ui.split_dialogs",
    "ui.stats_chart_widget",
    "ui.status_bar_manager",
    "ui.terminology_dialog",
    "ui.terminology_page",
    "ui.text_editor_dialog",
    "ui.text_editor_page",
    "ui.theme_manager_dialog",
    "ui.toast_widget",

    # Terminoloji Modülü
    "terminology",
    "terminology.terminology_manager",

    # Harici kütüphaneler - gizli bağımlılıklar
    "requests",
    "requests.adapters",
    "requests.auth",
    "google.genai",
    "openai",
    "tiktoken",
    "tiktoken.registry",
    "tiktoken_ext",
    "tiktoken_ext.openai_public",
    "ebooklib",
    "ebooklib.epub",
    "bs4",
    "numpy",
    "matplotlib",
    "langdetect",
    "deep_translator",
    "certifi",
]

# --- Veri Dosyaları ---
datas = [
    ("AppConfigs", "AppConfigs"),
    ("config", "config"),
]

if os.path.exists("logo64.ico"):
    datas.append(("logo64.ico", "."))
if os.path.exists("logo256.ico"):
    datas.append(("logo256.ico", "."))

# certifi cacert.pem dahil et
try:
    import certifi
    cacert = certifi.where()
    if os.path.exists(cacert):
        datas.append((cacert, "certifi"))
except ImportError:
    pass

# transformers model verilerini dahil et
try:
    datas += collect_data_files("transformers")
except Exception:
    pass

try:
    datas += collect_data_files("tiktoken")
except Exception:
    pass

try:
    datas += collect_data_files("ebooklib")
except Exception:
    pass

# --- Hariç Tutulanlar ---
excludes = [
    "tkinter",
    "scipy",
    "pandas",
    "PIL",
    "PySide6",
    "PyQt5",
    "IPython",
    "jupyter",
    "notebook",
    "pytest",
]

# ----------------------------------------------------------------
# ANALİZ AŞAMASI
# ----------------------------------------------------------------
a = Analysis(
    ["main_window.py"],           # Ana giriş dosyası
    pathex=["."],                 # Proje kök dizini
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

# ----------------------------------------------------------------
# PAKET AŞAMASI
# ----------------------------------------------------------------
pyz = PYZ(a.pure)

# ----------------------------------------------------------------
# ÇALIŞTIRILABILIR DOSYA
# ----------------------------------------------------------------
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,       # Tek dosya yerine klasör (daha kararlı)
    name="CeviriUygulamasi",
    debug=False,                 # Hata ayıklamak için True yapın
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,                    # UPX kuruluysa dosya boyutunu küçültür
    console=False,               # GUI uygulama - konsol penceresi açılmaz
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="logo256.ico" if os.path.exists("logo256.ico") else None,
)

# ----------------------------------------------------------------
# DAĞITIM KLASÖRÜ (dist/CeviriUygulamasi/)
# ----------------------------------------------------------------
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="CeviriUygulamasi",
)
