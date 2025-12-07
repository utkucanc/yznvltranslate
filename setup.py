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
    "temizlik",
    "chapter_check_worker" # Yeni eklenen modül - Bölüm başlığı kontrolü için
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
    "logo.ico"
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
    icon="logo.ico"
)

# --- Kurulum ---
#python setup.py bdist_msi
setup(
    name="NovelAlemCeviriAraci",
    version="1.9.3", # Sürümünüz (main_window.py'den alındı)
    description="NovelAlem Çeviri Aracı",
    options={"build_exe": build_exe_options},
    executables=[executable]
)
