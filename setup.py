import sys
import os
from cx_Freeze import setup, Executable

print("setup.py çalışıyor...")
print("Kurulum parametreleri: bdist_msi veya build")
print("Örnek: python setup.py bdist_msi veya python setup.py build")
print("bdist_msi         = Kurulum (setup.exe) dosyası oluşturur")
print("build             = Çalıştırılabilir dosya (CeviriUygulamasi.exe) oluşturur.")
# --- Projenizin Yerel Modülleri ---
try:
    includes = [
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
        "dialogs",
        "logger",
        "core.workers.download_worker",
        "core.workers.translation_worker",
        "core.workers.cleaning_worker",
        "core.workers.translation_error_check_worker",
        "core.workers.merging_worker",
        "core.workers.epub_worker",
        "core.workers.token_counter",
        "core.workers.token_count_worker",
        "core.workers.local_token_count_worker",   
        "core.workers.prompt_generator",
        "core.workers.split_worker",
        "core.workers.jsonoutput",
        "core.workers.ml_terminology_extractor",
        "core.workers.ml_terminology_worker",       
        "core.chapter_check_worker",
        "core.utils",
        "core.llm_provider",
        "core.js_create",
        "core.token_controller",                    
        "core.theme_defaultCreate",                 
        "core.file_list_manager",
        "core.process_controller",
        "ui.request_counter_manager",
        "ui.text_editor_dialog",
        "ui.api_stats_dialog",
        "ui.app_settings_dialog",
        "ui.menu_bar_builder",
        "ui.right_panel_builder",
        "ui.status_bar_manager",
        "ui.file_table_interactions",
        "ui.file_table_manager",
        "ui.mcp_server_dialog",                     
        "ui.terminology_dialog",                    
        "ui.ml_terminology_range_dialog",           
        "cache.translation_cache",
        "terminology.terminology_manager",
    ]

    # --- Harici Kütüphaneler ---
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
        "ebooklib",
        "ui",
        "core",
        "numpy",
        "core.workers",
        "qt_material",   
    ]

    # --- Dahil Edilecek Ek Dosyalar ---
    include_files = [
        "logo64.ico",
        "logo256.ico",
        ("AppConfigs/themes", "AppConfigs/themes"),
    ]
    try:
        import qt_material
        import os as _os
        qt_material_dir = qt_material.__path__[0]
        include_files.append((qt_material_dir, "qt_material"))
    except ImportError:
        print("[UYARI] qt-material bulunamadı. Tema dosyaları dahil edilmedi.")

    # --- Hariç Tutulacaklar ---

    excludes = [
        "tkinter",
        "scipy",
        "pandas",
        "PIL",
        "PySide6",
        "PyQt5"
    ]

    # --- Build Ayarları ---
    build_exe_options = {
        "packages": packages,
        "includes": includes,
        "include_files": include_files,
        "excludes": excludes,
        "include_msvcr": True,
        "zip_exclude_packages": ["numpy"],
    }

    # --- Platforma Özel Ayarlar ---
    base = None
    if sys.platform == "win32":
        base = "gui"

    # --- Yürütülebilir Dosya Tanımı ---
    executable = Executable(
        script="main_window.py",
        base=base,
        target_name="CeviriUygulamasi.exe",
        icon="logo256.ico"
    )

    # --- Kurulum ---
    #python setup.py bdist_msi
    setup(
        name="NovelCeviriAraci",
        version="2.4.0",  
        description="Novel Çeviri Aracı v2.4.0",
        author="UtkuCanC",
        author_email="utkucancanatan@gmail.com",
        options={"build_exe": build_exe_options},
        executables=[executable]
    )
except Exception as e:
    print(f"Hata oluştu: {e}")    
    sys.exit(1)
