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

    # Proje modülleri
    "dialogs",
    "logger",
    "core.workers.download_worker",
    "core.workers.translation_worker",
    "core.workers.cleaning_worker",
    "core.workers.translation_error_check_worker",
    "core.workers.merging_worker",
    "core.workers.epub_worker",
    "core.workers.token_counter",
    "core.workers.prompt_generator",
    "core.workers.split_worker",
    "core.workers.jsonoutput",
    "core.workers.ml_terminology_extractor",
    "core.chapter_check_worker",
    "core.utils",
    "core.llm_provider",
    "core.js_create",
    "core.localization",
    "ui.request_counter_manager",
    "ui.text_editor_dialog",
    "ui.api_stats_dialog",
    "ui.app_settings_dialog",
    "ui.menu_bar_builder",
    "ui.right_panel_builder",
    "ui.status_bar_manager",
    "ui.file_table_interactions",
    "ui.file_table_manager",
    "cache.translation_cache",
    "terminology.terminology_manager",

    # Harici kütüphaneler - gizli bağımlılıklar
    "requests",
    "requests.adapters",
    "requests.auth",
    "selenium",
    "selenium.webdriver",
    "selenium.webdriver.chrome.service",
    "webdriver_manager",
    "webdriver_manager.chrome",
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
    "numpy.core",
    "numpy.core._methods",
    "numpy.lib.format",
    "numpy.lib.stride_tricks",
    "numpy.linalg",
    "numpy.fft",
    "numpy.random",
    "numpy.polynomial",
    "matplotlib",
    "matplotlib.backends.backend_qt5agg",
    "matplotlib.backends.backend_agg",

    # transformers gizli bağımlılıkları
    "transformers",
    "transformers.models.auto",
    "huggingface_hub",
    "filelock",
    "tokenizers",
    "safetensors",
]

# --- Veri Dosyaları ---
datas = [
    ("logo64.ico", "."),
    ("logo256.ico", "."),
]

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
    icon="logo256.ico",
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
