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
        "dialogs",
        "download_worker",
        "translation_worker",
        "cleaning_worker",
        "translation_error_check_worker",
        "chapter_check_worker",
        "merging_worker",
        "epub_worker",
        "token_counter",
        "utils",
        "request_counter_manager",
        "text_editor_dialog",
        "llm_provider",
        "prompt_generator",
        "split_worker", # Toplu bölüm ekleme için
        "logger",  # Uygulama genelinde loglama için
        "cache.translation_cache",
        "terminology.terminology_manager",
        "ml_terminology_extractor",
        "js_create"
    ]

    # --- Harici Kütüphaneler ---
    packages = [
        "PyQt6",
        "requests",
        "selenium",
        "webdriver_manager",
        "google.genai"
    ]

    # --- Dahil Edilecek Ek Dosyalar ---
    include_files = [
        "logo64.ico",
        "logo256.ico"
    ]

    # --- Hariç Tutulacaklar ---

    excludes = [
        "tkinter",
        "numpy",
        "scipy",
        "pandas",
        "matplotlib",
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
        version="2.0.0",  # MCP, PromtGen, Cache, Terminology güncellemesi
        description="Novel Çeviri Aracı v2.0",
        options={"build_exe": build_exe_options},
        executables=[executable]
    )
except Exception as e:
    print(f"Hata oluştu: {e}")    
    sys.exit(1)
