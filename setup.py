import sys
import os
from cx_Freeze import setup, Executable

# --- Projenizin Yerel Modülleri ---
includes = [
    "dialogs",
    "download_worker",
    "translation_worker",
    "cleaning_worker",
    "merging_worker",
    "token_counter",
    "utils",
    "temizlik"
]

# --- Harici Kütüphaneler ---
packages = [
    "PyQt6",
    "requests",
    "bs4",
    "google.generativeai",
    "configparser",
    "json",
    "re",
]

# --- Dahil Edilecek Ek Dosyalar ---
include_files = [
    "logo.png"
]

# --- Hariç Tutulacaklar ---
# DÜZELTME: RecursionError hatasını önlemek için 
# gereksiz bilimsel kütüphaneleri hariç tutuyoruz.
excludes = [
    "tkinter",
    "numpy",
    "scipy",
    "pandas",
    "matplotlib",
    "PIL"
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
    base = "Win32GUI"

# --- Yürütülebilir Dosya Tanımı ---
executable = Executable(
    script="main_window.py",
    base=base,
    target_name="CeviriUygulamasi.exe",
    icon="logo.png"
)

# --- Kurulum ---
setup(
    name="CeviriUygulamasi",
    version="1.9", # Sürümünüz (main_window.py'den alındı)
    description="Bu uygulama, web sitelerinden Novel içeriği indirmek, Gemini API kullanarak çevirmek, metinleri temizlemek ve seçili çevirileri birleştirmek için tasarlanmıştır.",
    options={"build_exe": build_exe_options},
    executables=[executable]
)
