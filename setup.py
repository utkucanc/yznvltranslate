# -*- coding: utf-8 -*-
"""

------------------------------------------------------------------------------
KULLANIM KOMUTLARI:
------------------------------------------------------------------------------

1. Taşınabilir Klasör (Portable Folder):
   python setup.py build
   -> Çıktı: build/NovelCeviriAraci-Portable/
   -> İçindeki CeviriUygulamasi.exe ve lib/ klasörü tamamen bağımsızdır.
   -> Python ve kütüphane kurulumu gerektirmeden doğrudan çift tıklanarak çalışır.

2. Taşınabilir ZIP Paketi (Portable ZIP Archive):
   python setup.py portable   (veya python setup.py zip)
   -> Çıktı: dist/NovelCeviriAraci-3.0.0-Portable.zip
   -> build işlemini tamamlar ve klasörü otomatik olarak tek bir ZIP dosyası yapar.

3. Windows Kurulum Dosyası (.msi Setup Installer):
   python setup.py bdist_msi
   -> Çıktı: dist/NovelCeviriAraci-3.0.0-win64.msi
   -> Windows Program Files içerisine kurulum yapar.
   -> Masaüstü ve Başlat Menüsü'ne kısayol ekler.
   -> Program Ekle/Kaldır'a simgesiyle birlikte kaydolur.

4. Konsol / Hata Ayıklama Modu (Debug with Console):
   python setup.py build --console
   -> Standart GUI modunda terminal penceresi gizlenir.
   -> Eğer bir hata/çökme analiz edilmek isteniyorsa --console parametresi ile
      konsol penceresi açık bir exe derlenebilir.

------------------------------------------------------------------------------
PYTHON KURULU OLMAYAN SİSTEMLER İÇİN ÖNEMLİ PARAMETRELER:
------------------------------------------------------------------------------
- include_msvcr=True:
    Microsoft Visual C++ Redistributable (vcruntime140.dll, ucrtbase.dll vb.)
    dosyalarını derlemeye gömer. Kullanıcının bilgisayarında C++ Runtime
    yüklü olmasa bile uygulama sorunsuz açılır.
- zip_exclude_packages=["*"]:
    Tüm Python kütüphanelerini library.zip içine gömmek yerine açık lib/
    klasörüne çıkarır. Bu sayede PyQt6, numpy, matplotlib, deep_translator
    gibi native DLL ve veri dosyaları içeren paketler çökme yaşamadan çalışır.
- include_files:
    AppConfigs (temalar, dil dosyaları, promtlar, versiyon ayarı),
    kazıyıcı js dosyaları, ikonlar ve SSL sertifikaları (certifi cacert.pem)
    derleme çıktısına eklenir.
==============================================================================
"""

import sys
import os
import shutil

# Windows konsolunda Türkçe karakterlerin düzgün görünmesi için UTF-8 ayarı
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# --- Bilgilendirme ve Yardım Metni ---
HELP_BANNER = """
======================================================================
  Novel Çeviri Aracı (v3.1.0) - cx_Freeze Dağıtım Sistemi
======================================================================
Komutlar:
  1. python setup.py build         -> Taşınabilir klasör (Portable)
  2. python setup.py portable      -> Taşınabilir ZIP paketi
  3. python setup.py bdist_msi     -> Windows MSI Kurulum Paketi

Parametreler:
  --console                        -> Hata ayıklama için konsol penceresini açar
======================================================================
"""

if len(sys.argv) == 1:
    print(HELP_BANNER)
    print("Örnek: python setup.py build veya python setup.py bdist_msi")
    sys.exit(0)

# --- Özel Parametrelerin İşlenmesi ---
is_portable_zip = False
is_console = False

if "--console" in sys.argv:
    is_console = True
    sys.argv.remove("--console")

if "portable" in sys.argv:
    is_portable_zip = True
    sys.argv.remove("portable")
    if "build" not in sys.argv and "build_exe" not in sys.argv:
        sys.argv.append("build")
elif "zip" in sys.argv:
    is_portable_zip = True
    sys.argv.remove("zip")
    if "build" not in sys.argv and "build_exe" not in sys.argv:
        sys.argv.append("build")

# --- cx_Freeze ve Modüller ---
from cx_Freeze import setup, Executable

APP_NAME = "NovelCeviriAraci"
APP_VERSION = "3.0.0"
APP_TITLE = "Novel Çeviri Aracı v3.1.0"
AUTHOR = "UtkuCanC"
AUTHOR_EMAIL = "utkucancanatan@gmail.com"
MAIN_SCRIPT = "main_window.py"
ICON_FILE = "logo256.ico"
BUILD_EXE_DIR = os.path.join("build", "NovelCeviriAraci-Portable")

try:
    # --------------------------------------------------------------------------
    # 1. Dahil Edilecek Yerel Modüller (Includes)
    # --------------------------------------------------------------------------
    includes = [
        # PyQt6 Temel
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
        "PyQt6.sip",

        # Kök Seviye Modüller
        "dialogs",
        "logger",

        # Core Modülleri
        "core",
        "core.chapter_check_worker",
        "core.database_manager",
        "core.download_controller",
        "core.file_list_manager",
        "core.free_translators",
        "core.js_create",
        "core.llm_provider",
        "core.localization",
        "core.merge_controller",
        "core.process_controller",
        "core.project_manager",
        "core.theme_defaultCreate",
        "core.theme_engine",
        "core.token_controller",
        "core.translation_controller",
        "core.ui_state_manager",
        "core.utils",

        # Core Workers
        "core.workers",
        "core.workers.cleaning_worker",
        "core.workers.download_worker",
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
        "core.workers.translation_worker",

        # UI Modülleri
        "ui",
        "ui.api_key_editor_dialog",
        "ui.api_stats_dialog",
        "ui.app_settings_dialog",
        "ui.automation_setup_dialog",
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
        "ui.post_download_dialog",
        "ui.project_page",
        "ui.project_settings_dialog",
        "ui.prompt_editor_dialog",
        "ui.request_counter_manager",
        "ui.right_panel_builder",
        "ui.selenium_menu_dialog",
        "ui.sidebar_builder",
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
        "terminology.terminology_manager",
    ]

    # --------------------------------------------------------------------------
    # 2. Harici Python Paketleri (Packages)
    # --------------------------------------------------------------------------
    packages = [
        "PyQt6",
        "requests",
        "selenium",
        "webdriver_manager",
        "google.genai",
        "transformers",
        "matplotlib",
        "bs4",
        "openai",
        "tiktoken",
        "langdetect",
        "ebooklib",
        "numpy",
        "qt_material",
        "deep_translator",     # 'deep-translator' değil, Python modül adı 'deep_translator'
        "certifi",             # SSL sertifikaları için zorunlu
        "charset_normalizer",
        "urllib3",
        "idna",
        "ui",
        "core",
        "terminology",
    ]

    # --------------------------------------------------------------------------
    # 3. Dahil Edilecek Ek Dosyalar ve Klasörler (Include Files)
    # --------------------------------------------------------------------------
    include_files = []

    def add_file_if_exists(src, dst=None):
        """Dosya veya klasör mevcutsa include_files listesine ekler."""
        if os.path.exists(src):
            include_files.append((src, dst if dst else src))

    # İkonlar
    add_file_if_exists("logo64.ico", "logo64.ico")
    add_file_if_exists("logo256.ico", "logo256.ico")

    # Scraper (Kazıyıcı) JavaScript Dosyaları
    add_file_if_exists("69shuba.js", "69shuba.js")
    add_file_if_exists("booktoki.js", "booktoki.js")
    add_file_if_exists("novelfire.js", "novelfire.js")

    # Yapılandırma, Dil ve Tema Klasörleri
    add_file_if_exists("AppConfigs/themes", "AppConfigs/themes")
    add_file_if_exists("AppConfigs/locales", "AppConfigs/locales")
    add_file_if_exists("AppConfigs/Promts", "AppConfigs/Promts")
    add_file_if_exists("AppConfigs/GVersion.ini", "AppConfigs/GVersion.ini")
    add_file_if_exists("AppConfigs/app_settings.json", "AppConfigs/app_settings.json")
    add_file_if_exists("AppConfigs/MCP_Endpoints.json", "AppConfigs/MCP_Endpoints.json")

    # qt_material tema kaynak dosyaları
    try:
        import PyQt6  # qt_material'den önce import edilmeli
        import qt_material
        qt_material_dir = qt_material.__path__[0]
        add_file_if_exists(qt_material_dir, "qt_material")
        add_file_if_exists(qt_material_dir, "lib/qt_material")
    except ImportError:
        print("[UYARI] qt-material bulunamadı. Tema dosyaları dahil edilmedi.")

    # SSL Doğrulaması (certifi cacert.pem) - Python olmayan sistemlerde HTTPS bağlantıları için şart
    try:
        import certifi
        cacert = certifi.where()
        if os.path.exists(cacert):
            add_file_if_exists(cacert, "certifi/cacert.pem")
            add_file_if_exists(cacert, "cacert.pem")
    except ImportError:
        pass

    # --------------------------------------------------------------------------
    # 4. Hariç Tutulacak Paketler (Excludes - Boyutu küçültmek için)
    # --------------------------------------------------------------------------
    excludes = [
        "tkinter",
        "scipy",
        "pandas",
        "PIL",
        "PySide6",
        "PyQt5",
        "unittest",
        "test",
        "IPython",
        "jupyter",
        "notebook",
        "pytest",
    ]

    # --------------------------------------------------------------------------
    # 5. Build Seçenekleri (build_exe options)
    # --------------------------------------------------------------------------
    build_exe_options = {
        "build_exe": BUILD_EXE_DIR,       # Portable çıktı klasörü
        "packages": packages,
        "includes": includes,
        "include_files": include_files,
        "excludes": excludes,
        "include_msvcr": True,            # MSVC++ Runtime (VCRUNTIME140 vb.) dahil edilir
        "zip_include_packages": [],       # library.zip içine gömme
        "zip_exclude_packages": ["*"],    # Tüm paketler lib/ klasörüne çıkarılır (kararlılık için)
        "silent_level": 1,
    }

    # --------------------------------------------------------------------------
    # 6. Windows MSI Kurulum Paketi Seçenekleri (bdist_msi options)
    # --------------------------------------------------------------------------
    # Masaüstü ve Başlat Menüsü kısayolları için MSI tablosu:
    shortcut_table = [
        (
            "DesktopShortcut",                 # Shortcut
            "DesktopFolder",                   # Directory_
            "Novel Çeviri Aracı",              # Name
            "TARGETDIR",                       # Component_
            "[TARGETDIR]CeviriUygulamasi.exe", # Target
            None,                              # Arguments
            APP_TITLE,                         # Description
            None,                              # Hotkey
            None,                              # Icon_
            None,                              # IconIndex
            None,                              # ShowCmd
            "TARGETDIR",                       # WkDir
        ),
        (
            "ProgramMenuShortcut",             # Shortcut
            "ProgramMenuFolder",               # Directory_
            "Novel Çeviri Aracı",              # Name
            "TARGETDIR",                       # Component_
            "[TARGETDIR]CeviriUygulamasi.exe", # Target
            None,                              # Arguments
            APP_TITLE,                         # Description
            None,                              # Hotkey
            None,                              # Icon_
            None,                              # IconIndex
            None,                              # ShowCmd
            "TARGETDIR",                       # WkDir
        ),
    ]

    bdist_msi_options = {
        "data": {"Shortcut": shortcut_table},
        "upgrade_code": "{A3B5F6C7-8D9E-4F01-B2C3-D4E5F6A7B8C9}",
        "install_icon": ICON_FILE if os.path.exists(ICON_FILE) else None,
        "initial_target_dir": r"[ProgramFilesFolder]\NovelCeviriAraci",
        "summary_data": {
            "author": AUTHOR,
            "comments": f"{APP_TITLE} Kurulum Dosyası",
            "keywords": "Novel, Çeviri, Translation, AI, Gemini, DeepL, Yandex",
        },
    }

    # --------------------------------------------------------------------------
    # 7. Platform Tabanı ve Executable Tanımı
    # --------------------------------------------------------------------------
    if is_console:
        base = None
        print("[BİLGİ] Konsol modu aktif: Terminal çıktısı görünecektir.")
    else:
        base = "gui" if sys.platform == "win32" else None

    executable = Executable(
        script=MAIN_SCRIPT,
        base=base,
        target_name="CeviriUygulamasi.exe",
        icon=ICON_FILE if os.path.exists(ICON_FILE) else None,
    )

    # --------------------------------------------------------------------------
    # 8. Setup Çağrısı
    # --------------------------------------------------------------------------
    setup(
        name=APP_NAME,
        version=APP_VERSION,
        description=APP_TITLE,
        author=AUTHOR,
        author_email=AUTHOR_EMAIL,
        options={
            "build_exe": build_exe_options,
            "bdist_msi": bdist_msi_options,
        },
        executables=[executable],
    )

    # --------------------------------------------------------------------------
    # 9. Otomatik Taşınabilir ZIP Arşivi Oluşturma (portable / zip komutu)
    # --------------------------------------------------------------------------
    if is_portable_zip:
        dist_dir = os.path.join(os.path.dirname(__file__), "dist")
        os.makedirs(dist_dir, exist_ok=True)
        zip_output_base = os.path.join(dist_dir, f"{APP_NAME}-{APP_VERSION}-Portable")

        print("\n" + "=" * 70)
        print(f"[PORTABLE] '{BUILD_EXE_DIR}' klasörü ZIP olarak paketleniyor...")
        archive_path = shutil.make_archive(zip_output_base, "zip", BUILD_EXE_DIR)
        print(f"[BAŞARILI] Taşınabilir Portable ZIP hazırlandı:")
        print(f"           -> {archive_path}")
        print("=" * 70)

except Exception as e:
    print(f"\n[HATA] Derleme sırasında bir hata oluştu: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
