import sys
import os
import configparser
import json
import re
import shutil
import subprocess
import time
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QMenuBar, QListWidget, 
    QTableWidget, QTableWidgetItem, QPushButton, QHBoxLayout, 
    QVBoxLayout, QHeaderView, QCheckBox, QSizePolicy,  # QCheckBox eklendi
    QMessageBox, QProgressBar, QLabel, QMenu, QSpinBox
)
from PyQt6.QtGui import QFont, QColor, QAction
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject, QTimer

# Kendi oluşturduğumuz modülleri içe aktarıyoruz
#python -m PyInstaller --onefile --windowed main_window.py
from dialogs import NewProjectDialog, ProjectSettingsDialog, PromptEditorDialog, ApiKeyEditorDialog, GeminiVersionDialog
from download_worker import DownloadWorker
from translation_worker import TranslationWorker
from cleaning_worker import CleaningWorker
from merging_worker import MergingWorker
from token_counter import count_tokens_in_file, load_token_data, save_token_data 
from utils import format_file_size, natural_sort_key
from chapter_check_worker import ChapterCheckWorker # Yeni worker eklendi

class TokenCountWorker(QObject):
    finished = pyqtSignal(dict) # Tüm token verilerini döndür
    progress = pyqtSignal(int, int) # Current file index, total files
    error = pyqtSignal(str)

    def __init__(self, project_path, api_key, current_token_cache, model_version):
        super().__init__()
        self.project_path = project_path
        self.api_key = api_key
        self.is_running = True
        self.current_token_cache = current_token_cache # Mevcut önbellek (dict)
        self.model_version = model_version
        self.token_data_to_save = {"file_token_data": {}, "total_original_tokens": 0, "total_translated_tokens": 0, "total_combined_tokens": 0}


    def run(self):
        original_folder = os.path.join(self.project_path, 'dwnld')
        translated_folder = os.path.join(self.project_path, 'trslt')
        completed_folder = os.path.join(self.project_path, 'cmplt')

        total_original_tokens_sum = 0
        total_translated_tokens_sum = 0
        
        # Dosya listelerini oluştur
        original_files = sorted([f for f in os.listdir(original_folder) if f.endswith('.txt')]) if os.path.exists(original_folder) else []
        translated_files = sorted([f for f in os.listdir(translated_folder) if f.startswith('translated_') and f.endswith('.txt')]) if os.path.exists(translated_folder) else []
        merged_files = sorted([f for f in os.listdir(completed_folder) if f.startswith('merged_') and f.endswith('.txt')]) if os.path.exists(completed_folder) else []

        all_relevant_files = [] # {filename, path, type (original/translated/merged)}
        for f in original_files:
            all_relevant_files.append({'name': f, 'path': os.path.join(original_folder, f), 'type': 'original'})
        for f in translated_files:
            all_relevant_files.append({'name': f, 'path': os.path.join(translated_folder, f), 'type': 'translated'})
        for f in merged_files:
            all_relevant_files.append({'name': f, 'path': os.path.join(completed_folder, f), 'type': 'merged'})
        
        total_files_to_check = len(all_relevant_files)
        processed_count = 0

        # Her bir dosyayı işle
        for file_info in all_relevant_files:
            if not self.is_running: 
                break

            file_name = file_info['name']
            file_path = file_info['path']
            file_type = file_info['type']
            
            # Önbellekte dosya verisini ara
            cached_data = self.current_token_cache.get("file_token_data", {}).get(file_name)
            
            current_mtime = os.path.getmtime(file_path) # Mevcut değiştirme zamanı
            
            token_count = None
            should_recount = True

            if cached_data:
                # Cache'de mtime kontrolü yap
                if file_type == 'original' and cached_data.get('original_mtime') == current_mtime:
                    token_count = cached_data.get('original_tokens')
                    should_recount = False
                elif file_type == 'translated' and cached_data.get('translated_mtime') == current_mtime:
                    token_count = cached_data.get('translated_tokens')
                    should_recount = False
                elif file_type == 'merged' and cached_data.get('merged_mtime') == current_mtime: # merged dosyalar için ayrı mtime
                    token_count = cached_data.get('merged_tokens')
                    should_recount = False
            
            if should_recount:
                tokens, err = count_tokens_in_file(file_path, self.api_key, self.model_version)
                if tokens is not None:
                    token_count = tokens
                else:
                    print(f"Token sayım hatası ({file_name}): {err}") # Konsola hata bas
            
            # Sonuçları işçi verisine kaydet
            if file_name not in self.token_data_to_save["file_token_data"]:
                self.token_data_to_save["file_token_data"][file_name] = {
                    "original_tokens": None, "original_mtime": None,
                    "translated_tokens": None, "translated_mtime": None,
                    "merged_tokens": None, "merged_mtime": None
                }
            
            if file_type == 'original':
                self.token_data_to_save["file_token_data"][file_name]["original_tokens"] = token_count
                self.token_data_to_save["file_token_data"][file_name]["original_mtime"] = current_mtime
                if token_count is not None:
                    total_original_tokens_sum += token_count
            elif file_type == 'translated':
                self.token_data_to_save["file_token_data"][file_name]["translated_tokens"] = token_count
                self.token_data_to_save["file_token_data"][file_name]["translated_mtime"] = current_mtime
                if token_count is not None:
                    total_translated_tokens_sum += token_count
            elif file_type == 'merged':
                # Birleştirilmiş dosyalar genellikle 'translated_...' ön ekiyle ilişkilendirilmez
                # Bu yüzden sadece merged_tokens ve mtime'ı güncelleriz.
                self.token_data_to_save["file_token_data"][file_name]["merged_tokens"] = token_count
                self.token_data_to_save["file_token_data"][file_name]["merged_mtime"] = current_mtime
                

            processed_count += 1
            self.progress.emit(processed_count, total_files_to_check)

        self.token_data_to_save["total_original_tokens"] = total_original_tokens_sum
        self.token_data_to_save["total_translated_tokens"] = total_translated_tokens_sum
        self.token_data_to_save["total_combined_tokens"] = total_original_tokens_sum + total_translated_tokens_sum

        self.finished.emit(self.token_data_to_save)
    
    def stop(self):
        self.is_running = False

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Proje Yönetim Arayüzü")
        self.setGeometry(100, 100, 1400, 800) # Pencere boyutu büyütüldü
        
        # İş parçacığı referansları
        self.download_thread = None
        self.download_worker = None
        self.translation_thread = None
        self.translation_worker = None
        self.cleaning_thread = None
        self.cleaning_worker = None
        self.merging_thread = None
        self.merging_worker = None
        self.token_count_thread = None 
        self.token_count_worker = None
        self.chapter_check_thread = None  # Yeni: Başlık kontrolü için thread
        self.chapter_check_worker = None  # Yeni: Başlık kontrolü için worker

        self._ensure_app_structure()
        self.current_project_path = None 
        self.config = configparser.ConfigParser() 
        self.project_token_cache = {} # Her proje için token verilerini bellekte tutmak için

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)

        self._create_menu_bar()
        self._create_left_panel()
        self._create_center_panel()
        self._create_right_panel()

        self.load_existing_projects() 
        
        # QTableWidget için keyPressEvent'i yakala
        self.file_table.keyPressEvent = self.table_key_press_event

        # Token sayma işlemi için UI elemanlarını başlangıçta gizle
        self.total_tokens_label.setVisible(False)
        self.total_original_tokens_label.setVisible(False)
        self.total_translated_tokens_label.setVisible(False)
        self.token_progress_bar.setVisible(False)
        self.token_count_button.setEnabled(False) # Başlangıçta pasif
    def _ensure_app_structure(self):
        base_path = os.getcwd()
        paths = [
            os.path.join(base_path, "AppConfigs"),
            os.path.join(base_path, "AppConfigs", "Promts"),
            os.path.join(base_path, "AppConfigs", "APIKeys")
        ]
        try:
            for p in paths:
                if not os.path.exists(p): os.makedirs(p)
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Klasör yapısı oluşturulamadı: {e}")

    def get_gemini_model_version(self):
        """AppConfigs/GVersion.ini dosyasından versiyonu okur."""
        base_path = os.getcwd()
        config_path = os.path.join(base_path, "AppConfigs", "GVersion.ini")
        config = configparser.ConfigParser()
        if os.path.exists(config_path):
            config.read(config_path)
            return config.get("Version", "model_name", fallback="gemini-2.5-flash-preview-09-2025")
        return "gemini-2.5-flash-preview-09-2025"
    
    def _create_menu_bar(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("Dosya")
        new_project_action = file_menu.addAction("Yeni Proje")
        new_project_action.triggered.connect(self.new_project_clicked)
        # "Kaydet" menü öğesini "Proje Ayarları" fonksiyonuna bağlayalım
        save_action = file_menu.addAction("Ayarları Kaydet") # Aslında proje ayarlarını açacak
        save_action.triggered.connect(self.open_project_settings_dialog) 
        exit_action = file_menu.addAction("Çıkış")
        exit_action.triggered.connect(self.close)

        project_menu = menu_bar.addMenu("Proje")
        delete_project_action = project_menu.addAction("Proje Sil")
        delete_project_action.triggered.connect(self.delete_project_clicked)
        
        project_settings_action = project_menu.addAction("Proje Ayarları")
        project_settings_action.triggered.connect(self.open_project_settings_dialog)
        # --- YENİ AYARLAR MENÜSÜ ---
        settings_menu = menu_bar.addMenu("Ayarlar")
        prompt_editor_action = settings_menu.addAction("Promt Editörü")
        prompt_editor_action.triggered.connect(self.open_prompt_editor)
        
        apikey_editor_action = settings_menu.addAction("API Key Editörü")
        apikey_editor_action.triggered.connect(self.open_apikey_editor)
        
        gemini_version_action = settings_menu.addAction("Gemini Versiyon")
        gemini_version_action.triggered.connect(self.open_gemini_version_dialog)

        help_menu = menu_bar.addMenu("Yardım")
        about_action = help_menu.addAction("Hakkında")
        about_action.triggered.connect(self.show_about_dialog)

    def open_prompt_editor(self):
        PromptEditorDialog(self).exec()

    def open_apikey_editor(self):
        ApiKeyEditorDialog(self).exec()
        
    def open_gemini_version_dialog(self):
        GeminiVersionDialog(self).exec()

    def _create_left_panel(self):
        left_layout = QVBoxLayout()
        self.project_list = QListWidget()
        self.project_list.setFont(QFont("Arial", 10)) 
        self.project_list.currentItemChanged.connect(self.update_file_list_from_selection)
        self.project_list.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Expanding)
        self.project_list.setMaximumWidth(250)
        left_layout.addWidget(QLabel("Projeler:")) 
        left_layout.addWidget(self.project_list)
        self.main_layout.addLayout(left_layout, 1)

    def _create_center_panel(self):
        center_layout = QVBoxLayout()
        self.file_table = QTableWidget()
        # Yeni sütunlar eklendi: Orijinal Token, Çevrilen Token
        self.file_table.setColumnCount(8) 
        headers = ["Seç", "Orijinal Dosya", "Çevrilen Dosya", "Oluşturma Tarihi", "Boyut", "Durum", "Orijinal Token", "Çevrilen Token"] 
        self.file_table.setHorizontalHeaderLabels(headers)
        self.file_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # Seç
        self.file_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch) # Orijinal Dosya
        self.file_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch) # Çevrilen Dosya
        self.file_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents) # Oluşturma Tarihi
        self.file_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents) # Boyut
        self.file_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch) # Durum
        self.file_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents) # Orijinal Token (Yeni)
        self.file_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents) # Çevrilen Token (Yeni)
        self.file_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows) 
        self.file_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers) 
        center_layout.addWidget(self.file_table)
        self.main_layout.addLayout(center_layout, 4)

        # Sağ tıklama menüsü için ayarlar
        self.file_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.file_table.customContextMenuRequested.connect(self.file_table_context_menu)


    def _create_right_panel(self):
        right_layout = QVBoxLayout()
        
        self.startButton = QPushButton("İndirmeyi Başlat")
        self.startButton.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.startButton.setStyleSheet("background-color: #4CAF50; color: white; border-radius: 5px; padding: 10px;")
        self.startButton.clicked.connect(self.start_download_process)
        right_layout.addWidget(self.startButton)

        self.translateButton = QPushButton("Seçilenleri Çevir") 
        self.translateButton.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.translateButton.setStyleSheet("background-color: #2196F3; color: white; border-radius: 5px; padding: 10px;") 
        self.translateButton.clicked.connect(self.start_translation_process)
        self.translateButton.setEnabled(False) 
        right_layout.addWidget(self.translateButton)
        #   --- YENİ EKLENEN KISIM: SAYILI ÇEVİR ---
        limit_layout = QHBoxLayout()
        self.limit_checkbox = QCheckBox("Sayılı çevir")
        self.limit_checkbox.setFont(QFont("Arial", 9))
        self.limit_checkbox.setToolTip("İşaretlenirse sadece yandaki sayı kadar dosya çevrilip durur.")
        
        self.limit_spinbox = QSpinBox()
        self.limit_spinbox.setMinimum(1)
        self.limit_spinbox.setMaximum(99999)
        self.limit_spinbox.setValue(10) # Varsayılan değer
        self.limit_spinbox.setEnabled(False) # Başlangıçta pasif
        
        # Checkbox işaretlenince spinbox aktif olsun
        self.limit_checkbox.toggled.connect(self.limit_spinbox.setEnabled)
        
        limit_layout.addWidget(self.limit_checkbox)
        limit_layout.addWidget(self.limit_spinbox)
        right_layout.addLayout(limit_layout)
        # --- YENİ CHECKBOX ---
        self.shutdown_checkbox = QCheckBox("Çeviri Bitince Bilgisayarı Kapat")
        self.shutdown_checkbox.setFont(QFont("Arial", 9))
        self.shutdown_checkbox.setStyleSheet("margin-left: 5px; margin-bottom: 5px;")
        self.shutdown_checkbox.toggled.connect(self.on_shutdown_checkbox_toggled) 
        right_layout.addWidget(self.shutdown_checkbox)
        # --- BİTİŞ ---

        self.cleanButton = QPushButton("Gereksiz Metin Temizleme") 
        self.cleanButton.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.cleanButton.setStyleSheet("background-color: #FF9800; color: white; border-radius: 5px; padding: 10px;") 
        self.cleanButton.clicked.connect(self.start_cleaning_process)
        self.cleanButton.setEnabled(False) 
        right_layout.addWidget(self.cleanButton)
        
        self.mergeButton = QPushButton("Seçili Çevirileri Birleştir") 
        self.mergeButton.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.mergeButton.setStyleSheet("background-color: #9C27B0; color: white; border-radius: 5px; padding: 10px;") 
        self.mergeButton.clicked.connect(self.start_merging_process)
        self.mergeButton.setEnabled(False) 
        right_layout.addWidget(self.mergeButton)

        # --- YENİ: Başlık Kontrolü Butonu ---
        self.chapterCheckButton = QPushButton("Başlık Kontrolü")
        self.chapterCheckButton.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.chapterCheckButton.setStyleSheet("background-color: #009688; color: white; border-radius: 5px; padding: 10px;") # Teal renk
        self.chapterCheckButton.clicked.connect(self.start_chapter_check_process)
        self.chapterCheckButton.setEnabled(False)
        right_layout.addWidget(self.chapterCheckButton)
        # ------------------------------------

        # Yeni Token Say butonu eklendi
        self.token_count_button = QPushButton("Token Say")
        self.token_count_button.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.token_count_button.setStyleSheet("background-color: #673AB7; color: white; border-radius: 5px; padding: 10px;") # Mor ton
        self.token_count_button.clicked.connect(self.start_token_counting_manually)
        self.token_count_button.setEnabled(False) # Başlangıçta pasif
        right_layout.addWidget(self.token_count_button)

        self.progressBar = QProgressBar(self)
        self.progressBar.setTextVisible(True)
        self.progressBar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progressBar.setVisible(False) 
        right_layout.addWidget(self.progressBar)
        
        self.statusLabel = QLabel("Durum: Hazır")
        self.statusLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.statusLabel.setFont(QFont("Arial", 10))
        right_layout.addWidget(self.statusLabel)

        # Yeni token bilgileri ve ilerleme çubuğu
        self.total_tokens_label = QLabel("Toplam Token: 0")
        self.total_original_tokens_label = QLabel("Orijinal Token: 0")
        self.total_translated_tokens_label = QLabel("Çevrilen Token: 0")
        self.token_progress_bar = QProgressBar(self)
        self.token_progress_bar.setTextVisible(True)
        self.token_progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.token_progress_bar.setVisible(False) # Başlangıçta gizli

        token_info_layout = QVBoxLayout()
        token_info_layout.addWidget(self.total_tokens_label)
        token_info_layout.addWidget(self.total_original_tokens_label)
        token_info_layout.addWidget(self.total_translated_tokens_label)
        token_info_layout.addWidget(self.token_progress_bar)
        right_layout.addLayout(token_info_layout) # Ana düzeneğe ekle

        self.selectHighlightedButton = QPushButton("Seç (Vurgulananları İşaretle)")
        self.selectHighlightedButton.setFont(QFont("Arial", 10))
        self.selectHighlightedButton.setStyleSheet("background-color: #607D8B; color: white; border-radius: 5px; padding: 7px;")
        self.selectHighlightedButton.clicked.connect(self.mark_highlighted_rows_checked)
        right_layout.addWidget(self.selectHighlightedButton)


        self.projectSettingsButton = QPushButton("Proje Ayarları") 
        self.projectSettingsButton.setFont(QFont("Arial", 10))
        self.projectSettingsButton.setStyleSheet("background-color: #008CBA; color: white; border-radius: 5px; padding: 7px;")
        self.projectSettingsButton.clicked.connect(self.open_project_settings_dialog) 
        right_layout.addWidget(self.projectSettingsButton)

        self.helpButton = QPushButton("Yardım")
        self.helpButton.setFont(QFont("Arial", 10))
        self.helpButton.setStyleSheet("background-color: #008CBA; color: white; border-radius: 5px; padding: 7px;")
        self.helpButton.clicked.connect(self.show_help_clicked)
        right_layout.addWidget(self.helpButton)
            
        right_layout.addStretch() 
        self.main_layout.addLayout(right_layout, 1)

    def on_shutdown_checkbox_toggled(self, checked):
        if checked:
            reply = QMessageBox.warning(self, "Otomatik Kapatma",
                                        "İşlem bitince bilgisayar ONAYSIZ kapatılacak.\nDevam?",
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                        QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                self.shutdown_checkbox.blockSignals(True)
                self.shutdown_checkbox.setChecked(False)
                self.shutdown_checkbox.blockSignals(False)

    def load_existing_projects(self):
        self.project_list.clear()
        current_dir = os.getcwd()
        for item in os.listdir(current_dir):
            full_path = os.path.join(current_dir, item)
            if os.path.isdir(full_path):
                config_file_path = os.path.join(full_path, 'config', 'config.ini')
                if os.path.exists(config_file_path):
                    self.project_list.addItem(item)
        if self.project_list.count() > 0:
            self.project_list.setCurrentRow(0) 

    def new_project_clicked(self):
        dialog = NewProjectDialog(self)
        if dialog.exec():
            project_name, project_link, max_pages, api_key, startpromt = dialog.get_data()
            if not project_name or not project_link:
                QMessageBox.warning(self, "Eksik Bilgi", "Proje adı ve linki boş bırakılamaz.")
                return
            # API Key'in boş olması durumunda uyarı verelim
            if not api_key:
                QMessageBox.warning(self, "API Key Eksik", "Çeviri ve token sayımı için Gemini API anahtarı gereklidir.")
            
            try:
                base_path = os.path.join(os.getcwd(), project_name)
                if os.path.exists(base_path):
                    QMessageBox.warning(self, "Hata", f"'{project_name}' adında bir proje zaten mevcut.")
                    return
                subfolders = ["dwnld", "trslt", "cmplt", "config"] 
                for folder in subfolders:
                    os.makedirs(os.path.join(base_path, folder))
                
                # Proje konfigürasyonunu kaydet
                self.config['ProjectInfo'] = {'link': project_link}
                if max_pages is not None:
                    self.config['ProjectInfo']['max_pages'] = str(max_pages)
                self.config['API'] = {'gemini_api_key': api_key} 
                self.config["Startpromt"] = {'startpromt': startpromt}  # Yeni başlangıç istemi ekleniyor
                config_path = os.path.join(base_path, 'config', 'config.ini') 
                with open(config_path, 'w', encoding='utf-8') as configfile:
                    self.config.write(configfile)
                
                self.project_list.addItem(project_name)
                QMessageBox.information(self, "Başarılı", f"'{project_name}' projesi başarıyla oluşturuldu.")
                self.project_list.setCurrentItem(self.project_list.findItems(project_name, Qt.MatchFlag.MatchExactly)[0])
            except OSError as e:
                QMessageBox.critical(self, "Dosya Hatası", f"Dizin oluşturulurken bir hata oluştu:\n{e}")
            except Exception as e:
                QMessageBox.critical(self, "Genel Hata", f"Proje oluşturulurken beklenmeyen bir hata oluştu:\n{e}")

    def delete_project_clicked(self):
        current_item = self.project_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Proje Seçilmedi", "Lütfen silmek istediğiniz projeyi seçin.")
            return

        project_name = current_item.text()
        reply = QMessageBox.question(self, 'Proje Sil', 
                                     f"'{project_name}' projesini ve tüm içeriğini silmek istediğinize emin misiniz? Bu işlem geri alınamaz.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                     QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            project_path = os.path.join(os.getcwd(), project_name)
            try:
                shutil.rmtree(project_path)
                self.project_list.takeItem(self.project_list.row(current_item))
                QMessageBox.information(self, "Başarılı", f"'{project_name}' projesi başarıyla silindi.")
                self.update_file_list_from_selection() 
            except OSError as e:
                QMessageBox.critical(self, "Silme Hatası", f"Proje silinirken bir hata oluştu:\n{e}")
            except Exception as e:
                QMessageBox.critical(self, "Genel Hata", f"Proje silinirken beklenmeyen bir hata oluştu:\n{e}")


    def start_download_process(self):
        current_item = self.project_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Proje Seçilmedi", "Lütfen sol listeden bir proje seçin.")
            return
        
        project_name = current_item.text()
        project_path = os.path.join(os.getcwd(), project_name)
        config_path = os.path.join(project_path, 'config', 'config.ini') 

        if not os.path.exists(config_path):
            QMessageBox.critical(self, "Hata", f"'{project_name}' projesi için config.ini bulunamadı. Lütfen projeyi yeniden oluşturun veya linki manuel girin.")
            return

        try:
            self.config.read(config_path)
            project_link = self.config.get('ProjectInfo', 'link', fallback=None)
            max_pages = self.config.getint('ProjectInfo', 'max_pages', fallback=None) 
            
            if not project_link:
                QMessageBox.critical(self, "Hata", "Config dosyasında proje linki bulunamadı!")
                return
        except configparser.Error as e:
            QMessageBox.critical(self, "Config Hatası", f"Config dosyası okunurken hata oluştu:\n{e}")
            return
        except Exception as e:
            QMessageBox.critical(self, "Genel Hata", f"Proje bilgileri okunurken beklenmeyen bir hata oluştu:\n{e}")
            return

        download_folder = os.path.join(project_path, 'dwnld')
        os.makedirs(download_folder, exist_ok=True) 

        # Önceki indirme tamamlanmamışsa durdur
        if self.download_thread and self.download_thread.isRunning():
            self.download_worker.stop()
            self.download_thread.quit()
            self.download_thread.wait() 
            self.download_thread = None
            self.download_worker = None

        self.download_thread = QThread()
        self.download_worker = DownloadWorker(project_link, download_folder, max_pages) 
        self.download_worker.moveToThread(self.download_thread)
        
        self.download_thread.started.connect(self.download_worker.run)
        self.download_worker.finished.connect(self.download_thread.quit)
        self.download_worker.finished.connect(self.download_worker.deleteLater)
        self.download_thread.finished.connect(self.download_thread.deleteLater)
        
        self.download_worker.file_downloaded.connect(self.add_file_to_table)
        self.download_worker.error.connect(self.on_download_error)
        self.download_worker.finished.connect(self.on_download_finished)
        self.download_worker.progress.connect(self.update_download_progress) 
        
        self.download_thread.start()
        self._set_ui_state_on_process_start(self.startButton, "İndiriliyor...", "#FFC107", "black", max_pages if max_pages else 0, "Durum: İndirme işlemi başlatıldı...")
        self.file_table.setRowCount(0) 

    def update_download_progress(self, current, total):
        self.progressBar.setValue(current)
        if total > 0:
            self.progressBar.setMaximum(total)
            self.statusLabel.setText(f"Durum: İndiriliyor... Sayfa {current}/{total}")
        else:
            self.statusLabel.setText(f"Durum: İndiriliyor... Sayfa {current}")

    def on_download_finished(self):
        QMessageBox.information(self, "Tamamlandı", "İndirme işlemi bitti.")
        self._set_ui_state_on_process_end(self.startButton, "İndirmeyi Başlat", "#4CAF50", "white", "Durum: Hazır")
        self.download_thread = None
        self.download_worker = None
        self.update_file_list_from_selection() 

    def on_download_error(self, message):
        QMessageBox.critical(self, "İndirme Hatası", f"Bir hata oluştu:\n{message}")
        self._set_ui_state_on_process_end(self.startButton, "İndirmeyi Başlat", "#FF5722", "white", f"Durum: Hata - {message}")
        self.download_thread = None
        self.download_worker = None

    def start_translation_process(self):
        # Eğer zaten çalışıyorsa duraklatma/devam etme mantığını işlet
        if self.translation_thread and self.translation_thread.isRunning():
            if self.translation_worker.is_paused:
                self.translation_worker.resume()
                self.translateButton.setText("Duraklat")
                self.translateButton.setStyleSheet("background-color: #FFC107; color: black; border-radius: 5px; padding: 10px;")
                self.statusLabel.setText("Durum: Çeviriye devam ediliyor...")
            else:
                self.translation_worker.pause()
                self.translateButton.setText("Devam Et")
                self.translateButton.setStyleSheet("background-color: #4CAF50; color: white; border-radius: 5px; padding: 10px;") # Yeşil
                self.statusLabel.setText("Durum: Çeviri duraklatıldı.")
            return
        # Yeni Başlatma
        current_item = self.project_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Proje Seçilmedi", "Lütfen sol listeden bir proje seçin.")
            return

        project_name = current_item.text()
        project_path = os.path.join(os.getcwd(), project_name)
        config_path = os.path.join(project_path, 'config', 'config.ini')

        if not os.path.exists(config_path):
            QMessageBox.critical(self, "Hata", f"'{project_name}' projesi için config.ini bulunamadı. API anahtarı okunamıyor.")
            return

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config.read_file(f)
            api_key = self.config.get('API', 'gemini_api_key', fallback=None)
            startpromt = self.config.get('Startpromt', 'startpromt', fallback=None)  # Yeni başlangıç istemi ekleniyor
            
            if not api_key:
                QMessageBox.critical(self, "API Anahtarı Eksik", "Seçili proje için Gemini API anahtarı bulunamadı. Lütfen yeni bir proje oluştururken veya ayarlar kısmından anahtarı girin.")
                return
        except configparser.Error as e:
            QMessageBox.critical(self, "Config Hatası", f"Config dosyası okunurken hata oluştu:\n{e}")
            return
        except Exception as e:
            QMessageBox.critical(self, "Genel Hata", f"API anahtarı okunurken beklenmeyen bir hata oluştu:\n{e}")
            return

        input_folder = os.path.join(project_path, 'dwnld')
        output_folder = os.path.join(project_path, 'trslt')
        
        # Ensure output folder exists before starting translation worker
        os.makedirs(output_folder, exist_ok=True)

        files_to_translate = [f for f in os.listdir(input_folder) if f.endswith('.txt')]
        if not files_to_translate:
            QMessageBox.information(self, "Dosya Yok", "İndirilenler klasöründe çevrilecek dosya bulunamadı.")
            return
        
        # Önceki çeviri tamamlanmamışsa durdur
        model_version = self.get_gemini_model_version()
        if self.translation_thread and self.translation_thread.isRunning():
            self.translation_worker.stop()
            self.translation_thread.quit()
            self.translation_thread.wait() # Thread'in bitmesini bekle
            self.translation_thread = None
            self.translation_worker = None
        file_limit = None
        if self.limit_checkbox.isChecked():
            file_limit = self.limit_spinbox.value()
        self.translation_thread = QThread()
        self.translation_worker = TranslationWorker(input_folder, output_folder, api_key, startpromt, model_version, file_limit=file_limit)
        
        self.translation_worker.shutdown_on_finish = self.shutdown_checkbox.isChecked()
        self.translation_worker.moveToThread(self.translation_thread)

        self.translation_thread.started.connect(self.translation_worker.run)
        self.translation_worker.finished.connect(self.translation_thread.quit)
        self.translation_worker.finished.connect(self.translation_worker.deleteLater)
        self.translation_thread.finished.connect(self.translation_thread.deleteLater)

        self.translation_worker.finished.connect(self.on_translation_finished) 
        self.translation_worker.error.connect(self.on_translation_error)
        self.translation_worker.progress.connect(self.update_translation_progress)

        self.translation_thread.start()
        
        # Buton durumlarını ayarla
        self.startButton.setEnabled(False)
        self.cleanButton.setEnabled(False) 
        self.mergeButton.setEnabled(False) 
        self.chapterCheckButton.setEnabled(False) # Deaktif
        self.projectSettingsButton.setEnabled(False) 
        self.token_count_button.setEnabled(False) 
        
        # Translate butonu "Duraklat" işlevi kazanır
        self.translateButton.setEnabled(True) 
        self.translateButton.setText("Duraklat")
        self.translateButton.setStyleSheet("background-color: #FFC107; color: black; border-radius: 5px; padding: 10px;") 
        
        self.progressBar.setValue(0)
        self.progressBar.setMaximum(len(files_to_translate))
        self.progressBar.setVisible(True)
        self.statusLabel.setText(f"Durum: Çeviri başlatıldı... (Model: {model_version})")


    def update_translation_progress(self, current, total):
        self.progressBar.setValue(current)
        self.progressBar.setMaximum(total)
        self.statusLabel.setText(f"Durum: Çevriliyor... Dosya {current}/{total}")

    def on_translation_finished(self, shutdown_requested): # --- YENİ: Parametre eklendi ---
        QMessageBox.information(self, "Tamamlandı", "Çeviri işlemi bitti.")
        self.startButton.setEnabled(True)
        self.translateButton.setEnabled(True)
        self.cleanButton.setEnabled(True) # Çeviri bitince temizleme aktif
        self.mergeButton.setEnabled(True) # Çeviri bitince birleştirme aktif
        self.chapterCheckButton.setEnabled(True) # Çeviri bitince başlık kontrol aktif
        self.projectSettingsButton.setEnabled(True) # İşlem bitince proje ayarları aktif
        self.token_count_button.setEnabled(True) # İşlem bitince Token Say aktif
        self.translateButton.setText("Seçilenleri Çevir")
        self.translateButton.setStyleSheet("background-color: #2196F3; color: white; border-radius: 5px; padding: 10px;")
        self.progressBar.setVisible(False)
        self.statusLabel.setText("Durum: Hazır")
        self.translation_thread = None
        self.translation_worker = None
        self.update_file_list_from_selection() # Çeviri bitince listeyi güncelle (errors included)

        # --- YENİ: Kapatma işlemini kontrol et ---
        if shutdown_requested:
            reply = QMessageBox.question(self, 'Bilgisayar Kapatılıyor', 
                                         "Çeviri tamamlandı. Bilgisayar 60 saniye içinde kapatılacak.\nİptal etmek istiyor musunuz?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                         QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self._cancel_shutdown_computer()
            else:
                self._shutdown_computer()
        # --- BİTİŞ ---

    def on_translation_error(self, message):
        # This catches general errors from TranslationWorker.run(), not file-specific ones.
        QMessageBox.critical(self, "Çeviri Hatası", f"Bir hata oluştu:\n{message}")
        self.startButton.setEnabled(True)
        self.translateButton.setEnabled(True)
        self.cleanButton.setEnabled(True) # Hata olsa bile temizleme aktif edilebilir
        self.mergeButton.setEnabled(True) # Hata olsa bile birleştirme aktif edilebilir
        self.chapterCheckButton.setEnabled(True) # Hata olsa bile başlık kontrol aktif
        self.projectSettingsButton.setEnabled(True) # Hata olsa bile proje ayarları aktif
        self.token_count_button.setEnabled(True) # Hata olsa bile Token Say aktif
        self.translateButton.setText("Seçilenleri Çevir")
        self.translateButton.setStyleSheet("background-color: #FF5722; color: white; border-radius: 5px; padding: 10px;")
        self.progressBar.setVisible(False)
        self.statusLabel.setText(f"Durum: Hata - {message}")
        self.translation_thread = None
        self.translation_worker = None
        self.update_file_list_from_selection() # Refresh to show any partial successes or errors

    # --- YENİ METOTLAR: Bilgisayarı kapatma/iptal etme ---
    def _shutdown_computer(self):
        """İşletim sistemine göre bilgisayarı 60 saniye içinde kapatır."""
        try:
            if sys.platform == "win32": os.system("shutdown /s /t 60")
            elif sys.platform == "darwin": os.system("sudo shutdown -h +1")
            else: os.system("shutdown +1") 
        except Exception as e: QMessageBox.critical(self, "Hata", str(e))

    def start_cleaning_process(self):
        current_item = self.project_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Proje Seçilmedi", "Lütfen sol listeden bir proje seçin.")
            return

        project_name = current_item.text()
        project_path = os.path.join(os.getcwd(), project_name)
        
        selected_file_paths = []
        for row in range(self.file_table.rowCount()):
            checkbox_item = self.file_table.item(row, 0)
            if checkbox_item and checkbox_item.checkState() == Qt.CheckState.Checked:
                original_file_name = self.file_table.item(row, 1).text()
                translated_file_name = self.file_table.item(row, 2).text()
                # Status column (column 5) now determines which file to clean
                current_display_status = self.file_table.item(row, 5).text() 
                
                # Prioritize cleaning the translated file if it exists and is relevant
                if translated_file_name and translated_file_name != "Yok":
                    file_path = os.path.join(project_path, 'trslt', translated_file_name)
                    if os.path.exists(file_path):
                        selected_file_paths.append(file_path)
                elif original_file_name and original_file_name != "Orijinali Yok":
                    # If no translated file, or it's not selected/relevant, try original
                    file_path = os.path.join(project_path, 'dwnld', original_file_name)
                    if os.path.exists(file_path):
                        selected_file_paths.append(file_path)


        if not selected_file_paths:
            QMessageBox.warning(self, "Dosya Seçilmedi", "Lütfen temizlemek için en az bir dosya seçin.")
            return
        
        # Önceki temizleme tamamlanmamışsa durdur
        if self.cleaning_thread and self.cleaning_thread.isRunning():
            self.cleaning_worker.stop()
            self.cleaning_thread.quit()
            self.cleaning_thread.wait() # Thread'in bitmesini bekle
            self.cleaning_thread = None
            self.cleaning_worker = None

        self.cleaning_thread = QThread()
        # Pass the trslt folder as cleaning_folder for saving errors, since it's common
        self.cleaning_worker = CleaningWorker(selected_file_paths, os.path.join(project_path, 'trslt'))
        self.cleaning_worker.moveToThread(self.cleaning_thread)

        self.cleaning_thread.started.connect(self.cleaning_worker.run)
        self.cleaning_worker.finished.connect(self.cleaning_thread.quit)
        self.cleaning_worker.finished.connect(self.cleaning_worker.deleteLater)
        self.cleaning_thread.finished.connect(self.cleaning_thread.deleteLater)

        self.cleaning_worker.finished.connect(self.on_cleaning_finished)
        self.cleaning_worker.error.connect(self.on_cleaning_error)
        self.cleaning_worker.progress.connect(self.update_cleaning_progress)

        self.cleaning_thread.start()
        self.startButton.setEnabled(False)
        self.translateButton.setEnabled(False)
        self.cleanButton.setEnabled(False)
        self.mergeButton.setEnabled(False) # Temizleme sırasında birleştirme devre dışı
        self.chapterCheckButton.setEnabled(False) # Deaktif
        self.projectSettingsButton.setEnabled(False) # İşlem sırasında proje ayarları devre dışı
        self.token_count_button.setEnabled(False) # İşlem sırasında Token Say devre dışı
        self.cleanButton.setText("Temizleniyor...")
        self.cleanButton.setStyleSheet("background-color: #FFC107; color: black; border-radius: 5px; padding: 10px;") # Sarı renk
        self.progressBar.setValue(0)
        self.progressBar.setMaximum(len(selected_file_paths))
        self.progressBar.setVisible(True)
        self.statusLabel.setText(f"Durum: {len(selected_file_paths)} dosya temizleniyor...")


    def update_cleaning_progress(self, current, total):
        self.progressBar.setValue(current)
        self.progressBar.setMaximum(total)
        self.statusLabel.setText(f"Durum: Temizleniyor... Dosya {current}/{total}")

    def on_cleaning_finished(self):
        QMessageBox.information(self, "Tamamlandı", "Metin temizleme işlemi bitti.")
        self.startButton.setEnabled(True)
        self.translateButton.setEnabled(True)
        self.cleanButton.setEnabled(True)
        self.mergeButton.setEnabled(True)
        self.chapterCheckButton.setEnabled(True)
        self.projectSettingsButton.setEnabled(True) # İşlem bitince proje ayarları aktif
        self.token_count_button.setEnabled(True) # İşlem bitince Token Say aktif
        self.cleanButton.setText("Gereksiz Metin Temizleme")
        self.cleanButton.setStyleSheet("background-color: #FF9800; color: white; border-radius: 5px; padding: 10px;")
        self.progressBar.setVisible(False)
        self.statusLabel.setText("Durum: Hazır")
        self.cleaning_thread = None
        self.cleaning_worker = None
        self.update_file_list_from_selection() # Temizleme bitince listeyi güncelle (errors included)

    def on_cleaning_error(self, message):
        QMessageBox.critical(self, "Temizleme Hatası", f"Bir hata oluştu:\n{message}")
        self.startButton.setEnabled(True)
        self.translateButton.setEnabled(True)
        self.cleanButton.setEnabled(True)
        self.mergeButton.setEnabled(True) # Hata olsa bile birleştirme aktif edilebilir
        self.chapterCheckButton.setEnabled(True)
        self.projectSettingsButton.setEnabled(True) # Hata olsa bile proje ayarları aktif
        self.token_count_button.setEnabled(True) # Hata olsa bile Token Say aktif
        self.cleanButton.setText("Gereksiz Metin Temizleme")
        self.cleanButton.setStyleSheet("background-color: #FF5722; color: white; border-radius: 5px; padding: 10px;") # Kırmızı renk
        self.progressBar.setVisible(False)
        self.statusLabel.setText(f"Durum: Hata - {message}")
        self.cleaning_thread = None
        self.cleaning_worker = None
        self.update_file_list_from_selection() # Refresh to show any partial successes or errors

    def start_merging_process(self):
        current_item = self.project_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Proje Seçilmedi", "Lütfen sol listeden bir proje seçin.")
            return

        project_name = current_item.text()
        project_path = os.path.join(os.getcwd(), project_name)
        
        selected_translated_file_paths = []
        for row in range(self.file_table.rowCount()):
            checkbox_item = self.file_table.item(row, 0)
            if checkbox_item and checkbox_item.checkState() == Qt.CheckState.Checked:
                translated_file_name = self.file_table.item(row, 2).text() # Sütun 2 çevrilen dosya adı
                if translated_file_name and translated_file_name != "Yok": # Sadece çevrilmiş dosyaları al
                    file_path = os.path.join(project_path, 'trslt', translated_file_name)
                    if os.path.exists(file_path):
                        selected_translated_file_paths.append(file_path)

        if not selected_translated_file_paths:
            QMessageBox.warning(self, "Dosya Seçilmedi", "Lütfen birleştirmek için çevrilmiş dosya seçin.")
            return
            
        # Dosyaları doğal sıraya göre sırala
        
        selected_translated_file_paths.sort(key=lambda x: natural_sort_key(os.path.basename(x)))

        # Önceki birleştirme tamamlanmamışsa durdur
        if self.merging_thread and self.merging_thread.isRunning():
            self.merging_worker.stop()
            self.merging_thread.quit()
            self.merging_thread.wait() # Thread'in bitmesini bekle
            self.merging_thread = None
            self.merging_worker = None

        output_merged_folder = os.path.join(project_path, 'cmplt')
        os.makedirs(output_merged_folder, exist_ok=True) # Ensure output folder exists
        
        self.merging_thread = QThread()
        self.merging_worker = MergingWorker(selected_translated_file_paths, output_merged_folder)
        self.merging_worker.moveToThread(self.merging_thread)
        
        self.merging_thread.started.connect(self.merging_worker.run)
        self.merging_worker.finished.connect(self.merging_thread.quit)
        self.merging_worker.finished.connect(self.merging_worker.deleteLater)
        self.merging_thread.finished.connect(self.merging_thread.deleteLater)
        
        self.merging_worker.finished.connect(self.on_merging_finished)
        self.merging_worker.error.connect(self.on_merging_error)
        self.merging_worker.progress.connect(self.update_merging_progress)
        
        self.merging_thread.start()
        self.startButton.setEnabled(False)
        self.translateButton.setEnabled(False)
        self.cleanButton.setEnabled(False)
        self.mergeButton.setEnabled(False)
        self.chapterCheckButton.setEnabled(False) # Deaktif
        self.projectSettingsButton.setEnabled(False) # İşlem sırasında proje ayarları devre dışı
        self.token_count_button.setEnabled(False) # İşlem sırasında Token Say devre dışı
        self.mergeButton.setText("Birleştiriliyor...")
        self.mergeButton.setStyleSheet("background-color: #FFC107; color: black; border-radius: 5px; padding: 10px;") # Sarı renk
        self.progressBar.setValue(0)
        self.progressBar.setMaximum(len(selected_translated_file_paths))
        self.progressBar.setVisible(True)
        self.statusLabel.setText(f"Durum: {len(selected_translated_file_paths)} dosya birleştiriliyor...")

    def update_merging_progress(self, current, total):
        self.progressBar.setValue(current)
        self.progressBar.setMaximum(total)
        self.statusLabel.setText(f"Durum: Birleştiriliyor... Dosya {current}/{total}")

    def on_merging_finished(self):
        QMessageBox.information(self, "Tamamlandı", "Seçili çevirileri birleştirme işlemi bitti.")
        self.startButton.setEnabled(True)
        self.translateButton.setEnabled(True)
        self.cleanButton.setEnabled(True)
        self.mergeButton.setEnabled(True)
        self.chapterCheckButton.setEnabled(True)
        self.projectSettingsButton.setEnabled(True) # İşlem bitince proje ayarları aktif
        self.token_count_button.setEnabled(True) # İşlem bitince Token Say aktif
        self.mergeButton.setText("Seçili Çevirileri Birleştir")
        self.mergeButton.setStyleSheet("background-color: #9C27B0; color: white; border-radius: 5px; padding: 10px;")
        self.progressBar.setVisible(False)
        self.statusLabel.setText("Durum: Hazır")
        self.merging_thread = None
        self.merging_worker = None
        self.update_file_list_from_selection() 

    def on_merging_error(self, message):
        QMessageBox.critical(self, "Birleştirme Hatası", f"Bir hata oluştu:\n{message}")
        self.startButton.setEnabled(True)
        self.translateButton.setEnabled(True)
        self.cleanButton.setEnabled(True)
        self.mergeButton.setEnabled(True)
        self.chapterCheckButton.setEnabled(True)
        self.projectSettingsButton.setEnabled(True) # Hata olsa bile proje ayarları aktif
        self.token_count_button.setEnabled(True) # Hata olsa bile Token Say aktif
        self.mergeButton.setText("Seçili Çevirileri Birleştir")
        self.mergeButton.setStyleSheet("background-color: #FF5722; color: white; border-radius: 5px; padding: 10px;")
        self.progressBar.setVisible(False)
        self.statusLabel.setText(f"Durum: Hata - {message}")
        self.merging_thread = None
        self.merging_worker = None
        self.update_file_list_from_selection() 

    # --- YENİ: Başlık Kontrolü Metotları ---
    def start_chapter_check_process(self):
        current_item = self.project_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Proje Seçilmedi", "Lütfen sol listeden bir proje seçin.")
            return

        project_name = current_item.text()
        project_path = os.path.join(os.getcwd(), project_name)
        
        # Kontrol edilecek dosyaları topla (Çevrilen Dosyalar)
        files_to_check = [] # List of (filename, full_path)
        for row in range(self.file_table.rowCount()):
            checkbox_item = self.file_table.item(row, 0)
            if checkbox_item and checkbox_item.checkState() == Qt.CheckState.Checked:
                translated_file_name = self.file_table.item(row, 2).text()
                if translated_file_name and translated_file_name != "Yok" and translated_file_name != "N/A":
                    file_path = os.path.join(project_path, 'trslt', translated_file_name)
                    files_to_check.append((translated_file_name, file_path))
        
        if not files_to_check:
             QMessageBox.warning(self, "Dosya Seçilmedi", "Lütfen başlık kontrolü için en az bir çevrilmiş dosya seçin.")
             return

        # Önceki işlem varsa durdur
        if self.chapter_check_thread and self.chapter_check_thread.isRunning():
            self.chapter_check_worker.stop()
            self.chapter_check_thread.quit()
            self.chapter_check_thread.wait()
            self.chapter_check_thread = None
            self.chapter_check_worker = None
        
        self.chapter_check_thread = QThread()
        self.chapter_check_worker = ChapterCheckWorker(project_path, files_to_check)
        self.chapter_check_worker.moveToThread(self.chapter_check_thread)

        self.chapter_check_thread.started.connect(self.chapter_check_worker.run)
        self.chapter_check_worker.finished.connect(self.chapter_check_thread.quit)
        self.chapter_check_worker.finished.connect(self.chapter_check_worker.deleteLater)
        self.chapter_check_thread.finished.connect(self.chapter_check_thread.deleteLater)

        self.chapter_check_worker.finished.connect(self.on_chapter_check_finished)
        self.chapter_check_worker.progress.connect(self.update_chapter_check_progress)
        self.chapter_check_worker.error.connect(self.on_chapter_check_error)

        self.chapter_check_thread.start()
        
        # UI Güncelleme
        self._set_ui_state_on_process_start(self.chapterCheckButton, "Kontrol Ediliyor...", "#FFC107", "black", len(files_to_check), "Durum: Başlıklar kontrol ediliyor...")

    def update_chapter_check_progress(self, current, total):
        self.progressBar.setValue(current)
        self.progressBar.setMaximum(total)
        self.statusLabel.setText(f"Durum: Kontrol ediliyor... Dosya {current}/{total}")

    def on_chapter_check_finished(self, message):
        QMessageBox.information(self, "Tamamlandı", message)
        self._set_ui_state_on_process_end(self.chapterCheckButton, "Başlık Kontrolü", "#009688", "white", "Durum: Hazır")
        self.chapter_check_thread = None
        self.chapter_check_worker = None

    def on_chapter_check_error(self, message):
        QMessageBox.critical(self, "Hata", message)
        self._set_ui_state_on_process_end(self.chapterCheckButton, "Başlık Kontrolü", "#FF5722", "white", f"Durum: Hata - {message}")
        self.chapter_check_thread = None
        self.chapter_check_worker = None
    # ---------------------------------------

    def _set_ui_state_on_process_start(self, button, text, bg_color, text_color, max_progress, status_text):
        """İşlem başladığında UI durumunu ayarlar."""
        self.startButton.setEnabled(False)
        self.translateButton.setEnabled(False)
        self.cleanButton.setEnabled(False)
        self.mergeButton.setEnabled(False)
        self.chapterCheckButton.setEnabled(False) # Yeni
        self.projectSettingsButton.setEnabled(False)
        self.selectHighlightedButton.setEnabled(False)
        self.token_count_button.setEnabled(False) # Yeni: Token Say butonu devre dışı
        button.setEnabled(False) 
        button.setText(text)
        button.setStyleSheet(f"background-color: {bg_color}; color: {text_color}; border-radius: 5px; padding: 10px;")
        self.progressBar.setValue(0)
        self.progressBar.setMaximum(max_progress)
        self.progressBar.setVisible(True)
        self.statusLabel.setText(status_text)
        self.total_tokens_label.setVisible(False) 
        self.total_original_tokens_label.setVisible(False)
        self.total_translated_tokens_label.setVisible(False)
        self.token_progress_bar.setVisible(False)

    def _set_ui_state_on_process_end(self, button, text, bg_color, text_color, status_text):
        """İşlem bittiğinde UI durumunu ayarlar."""
        self.startButton.setEnabled(True)
        self.translateButton.setEnabled(True)
        self.cleanButton.setEnabled(True)
        self.mergeButton.setEnabled(True)
        self.chapterCheckButton.setEnabled(True) # Yeni
        self.projectSettingsButton.setEnabled(True)
        self.selectHighlightedButton.setEnabled(True)
        self.token_count_button.setEnabled(True) # Yeni: Token Say butonu aktif
        button.setEnabled(True)
        button.setText(text)
        button.setStyleSheet(f"background-color: {bg_color}; color: {text_color}; border-radius: 5px; padding: 10px;")
        self.progressBar.setVisible(False)
        self.statusLabel.setText(status_text)
        # Token bilgileri işlem bittikten sonra görünür olacak (token sayımı zaten tetiklenecek)


    def update_file_list_from_selection(self):
        self.file_table.setRowCount(0)
        current_item = self.project_list.currentItem()
        if not current_item:
            self.current_project_path = None
            self.translateButton.setEnabled(False)
            self.cleanButton.setEnabled(False)
            self.mergeButton.setEnabled(False)
            self.chapterCheckButton.setEnabled(False) # Deaktif
            self.projectSettingsButton.setEnabled(False) 
            self.selectHighlightedButton.setEnabled(False) 
            self.token_count_button.setEnabled(False) # Proje yoksa pasif
            # Proje seçili değilken token bilgilerini sıfırla ve gizle
            self.total_tokens_label.setText("Toplam Token: 0")
            self.total_original_tokens_label.setText("Orijinal Token: 0")
            self.total_translated_tokens_label.setText("Çevrilen Token: 0")
            self.total_tokens_label.setVisible(False)
            self.total_original_tokens_label.setVisible(False)
            self.total_translated_tokens_label.setVisible(False)
            self.token_progress_bar.setVisible(False)
            return

        project_name = current_item.text()
        self.current_project_path = os.path.join(os.getcwd(), project_name)
        config_folder_path = os.path.join(self.current_project_path, 'config') # config klasörünün yolu
        download_folder = os.path.join(self.current_project_path, 'dwnld')
        translated_folder = os.path.join(self.current_project_path, 'trslt')
        completed_folder = os.path.join(self.current_project_path, 'cmplt') 

        self.translateButton.setEnabled(True)
        self.cleanButton.setEnabled(True)
        self.mergeButton.setEnabled(True)
        self.chapterCheckButton.setEnabled(True) # Aktif
        self.projectSettingsButton.setEnabled(True) 
        self.selectHighlightedButton.setEnabled(True) 
        self.token_count_button.setEnabled(True) # Proje seçilince aktif

        # Mevcut token önbelleğini yükle
        self.project_token_cache = load_token_data(config_folder_path)

        # Hata loglarını yükle
        translation_errors = {} 
        error_log_path_translation = os.path.join(translated_folder, 'translation_errors.json')
        if os.path.exists(error_log_path_translation):
            try:
                with open(error_log_path_translation, 'r', encoding='utf-8') as f:
                    translation_errors = json.load(f)
            except json.JSONDecodeError as e:
                print(f"Hata: '{error_log_path_translation}' okunurken JSON hatası: {e}")
                translation_errors = {}
            except Exception as e:
                print(f"Hata: '{error_log_path_translation}' okunurken genel hata: {e}")
                translation_errors = {}

        cleaning_errors = {}
        error_log_path_cleaning = os.path.join(translated_folder, 'cleaning_errors.json') 
        if os.path.exists(error_log_path_cleaning):
            try:
                with open(error_log_path_cleaning, 'r', encoding='utf-8') as f:
                    cleaning_errors = json.load(f)
            except json.JSONDecodeError as e:
                print(f"Hata: '{error_log_path_cleaning}' okunurken JSON hatası: {e}")
                cleaning_errors = {}
            except Exception as e:
                print(f"Hata: '{error_log_path_cleaning}' okunurken genel hata: {e}")
                cleaning_errors = {}


        file_data_map = {} 

        # Process downloaded files (originals)
        if os.path.exists(download_folder):
            dwnld_files = sorted([f for f in os.listdir(download_folder) if f.endswith('.txt')])
            for file_name in dwnld_files:
                original_file_base = file_name.replace(".txt", "")
                file_path = os.path.join(download_folder, file_name)
                
                try:
                    file_stat = os.stat(file_path)
                    creation_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(file_stat.st_ctime))
                    file_size = format_file_size(file_stat.st_size)
                except Exception:
                    creation_time, file_size = "Bilinmiyor", "Bilinmiyor"

                # Token bilgisini önbellekten al
                cached_tokens_data = self.project_token_cache.get("file_token_data", {}).get(file_name, {})
                original_token_count = cached_tokens_data.get("original_tokens", "Hesaplanmadı") # Yeni varsayılan değer
                
                file_data_map[original_file_base] = {
                    "original_file_name": file_name,
                    "original_file_path": file_path,
                    "original_creation_time": creation_time,
                    "original_file_size": file_size,
                    "translated_file_name": "", 
                    "translated_file_path": "",
                    "translation_status": "Çevrilmedi", 
                    "cleaning_status": "Temizlenmedi", 
                    "is_translated": False,
                    "is_cleaned": False,
                    "sort_key": original_file_base,
                    "original_token_count": original_token_count, 
                    "translated_token_count": "Yok" 
                }
                if file_name in cleaning_errors:
                    file_data_map[original_file_base]["cleaning_status"] = f"Hata: {cleaning_errors[file_name]}"


        # Process translated files and update map
        if os.path.exists(translated_folder):
            trslt_files = sorted([f for f in os.listdir(translated_folder) if f.startswith('translated_') and f.endswith('.txt')])
            for translated_file_name in trslt_files:
                original_file_name_candidate = translated_file_name.replace("translated_", "")
                original_file_base = original_file_name_candidate.replace(".txt", "")
                
                # Token bilgisini önbellekten al
                cached_tokens_data = self.project_token_cache.get("file_token_data", {}).get(translated_file_name, {})
                translated_token_count = cached_tokens_data.get("translated_tokens", "Hesaplanmadı") # Yeni varsayılan değer

                if original_file_base in file_data_map:
                    entry = file_data_map[original_file_base]
                    entry["translated_file_name"] = translated_file_name
                    entry["translated_file_path"] = os.path.join(translated_folder, translated_file_name)
                    entry["is_translated"] = True
                    entry["translated_token_count"] = translated_token_count 
                    
                    if original_file_name_candidate in translation_errors:
                        entry["translation_status"] = f"Hata: {translation_errors[original_file_name_candidate]}"
                    else:
                        entry["translation_status"] = "Çevrildi"
                    
                    if translated_file_name in cleaning_errors:
                        entry["cleaning_status"] = f"Hata: {cleaning_errors[translated_file_name]}"

                else:
                    translated_file_path = os.path.join(translated_folder, translated_file_name)
                    try:
                        file_stat = os.stat(translated_file_path)
                        creation_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(file_stat.st_ctime))
                        file_size = format_file_size(file_stat.st_size)
                    except Exception:
                        creation_time, file_size = "Bilinmiyor", "Bilinmiyor"

                    file_data_map[original_file_base] = { 
                        "original_file_name": "Orijinali Yok", 
                        "original_file_path": "",
                        "original_creation_time": creation_time, 
                        "original_file_size": file_size, 
                        "translated_file_name": translated_file_name,
                        "translated_file_path": translated_file_path,
                        "translation_status": "Orijinali Yok", 
                        "cleaning_status": "Temizlenmedi", 
                        "is_translated": True,
                        "is_cleaned": False,
                        "sort_key": original_file_base,
                        "original_token_count": "Yok", 
                        "translated_token_count": translated_token_count 
                    }
                    if translated_file_name in cleaning_errors:
                        file_data_map[original_file_base]["cleaning_status"] = f"Hata: {cleaning_errors[translated_file_name]}"

        # Process completed files (merged files) - these will appear as separate entries
        if os.path.exists(completed_folder):
            cmplt_files = sorted([f for f in os.listdir(completed_folder) if f.endswith('.txt')])
            for file_name in cmplt_files:
                merged_file_base = f"merged_{file_name.replace('.txt', '')}" 
                file_path = os.path.join(completed_folder, file_name)

                try:
                    file_stat = os.stat(file_path)
                    creation_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(file_stat.st_ctime))
                    file_size = format_file_size(file_stat.st_size)
                except Exception:
                    creation_time, file_size = "Bilinmiyor", "Bilinmiyor"
                
                # Token bilgisini önbellekten al
                cached_tokens_data = self.project_token_cache.get("file_token_data", {}).get(file_name, {})
                merged_token_count = cached_tokens_data.get("merged_tokens", "Hesaplanmadı") # Yeni varsayılan değer

                file_data_map[merged_file_base] = {
                    "original_file_name": "N/A", 
                    "original_file_path": "",
                    "original_creation_time": creation_time,
                    "original_file_size": file_size,
                    "translated_file_name": file_name, # Merged file is shown here
                    "translated_file_path": file_path,
                    "translation_status": "Birleştirildi", 
                    "cleaning_status": "N/A",
                    "is_translated": False, 
                    "is_cleaned": False,
                    "sort_key": merged_file_base,
                    "original_token_count": "N/A", 
                    "translated_token_count": merged_token_count 
                }

        # Combine translation and cleaning status into a single "Durum" for display
        for key, entry in file_data_map.items():
            final_status = ""
            
            if entry["translation_status"] == "Birleştirildi": 
                final_status = "Birleştirildi"
            elif entry["original_file_name"] == "Orijinali Yok":
                final_status = f"Orijinali Yok, {entry['translation_status']}"
            elif entry["translation_status"].startswith("Hata:"):
                final_status = entry["translation_status"] 
            elif entry["cleaning_status"].startswith("Hata:"):
                 final_status = entry["cleaning_status"] 
            elif entry["is_translated"]:
                final_status = entry["translation_status"] 
            else:
                final_status = "İndirildi" 

            entry["display_status"] = final_status


        sorted_entries = sorted(file_data_map.values(), key=lambda x: natural_sort_key(x["sort_key"]))

        self.file_table.setRowCount(len(sorted_entries))
        for row, entry_data in enumerate(sorted_entries):
            self.populate_table_row(row, entry_data)
        
        # Token sayımı burada otomatik başlatılmıyor, sadece butonla tetiklenecek
        # Ancak toplam token etiketlerini önbellekten yükleyelim (varsa)
        self.total_original_tokens_label.setText(f"Toplam Orijinal Token: {self.project_token_cache.get('total_original_tokens', 0)}")
        self.total_translated_tokens_label.setText(f"Toplam Çevrilen Token: {self.project_token_cache.get('total_translated_tokens', 0)}")
        self.total_tokens_label.setText(f"Toplam Token (Orijinal + Çevrilen): {self.project_token_cache.get('total_combined_tokens', 0)}")
        
        self.total_tokens_label.setVisible(True)
        self.total_original_tokens_label.setVisible(True)
        self.total_translated_tokens_label.setVisible(True)
        self.token_progress_bar.setVisible(False)


    def populate_table_row(self, row, entry_data):
        # Column 0: Checkbox
        checkbox_item = QTableWidgetItem()
        checkbox_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
        checkbox_item.setCheckState(Qt.CheckState.Unchecked)
        self.file_table.setItem(row, 0, checkbox_item)

        # Column 1: Original File Name
        self.file_table.setItem(row, 1, QTableWidgetItem(entry_data["original_file_name"]))

        # Column 2: Translated File Name
        self.file_table.setItem(row, 2, QTableWidgetItem(entry_data["translated_file_name"] if entry_data["translated_file_name"] else "Yok"))
        
        # Column 3: Creation Date (Original)
        self.file_table.setItem(row, 3, QTableWidgetItem(entry_data["original_creation_time"]))
        
        # Column 4: Size (Original)
        self.file_table.setItem(row, 4, QTableWidgetItem(entry_data["original_file_size"]))
        
        # Column 5: Status 
        status_text = entry_data["display_status"]
        status_item = QTableWidgetItem(status_text)
        
        if status_text.startswith("Hata:"):
            status_item.setForeground(QColor(Qt.GlobalColor.red)) 
        elif status_text == "Çevrildi" or status_text == "Birleştirildi": 
            status_item.setForeground(QColor(Qt.GlobalColor.darkGreen)) 
        elif status_text == "Orijinali Yok, Çevrildi":
            status_item.setForeground(QColor(Qt.GlobalColor.darkGreen)) 
        elif status_text == "Orijinali Yok":
            status_item.setForeground(QColor(Qt.GlobalColor.darkMagenta)) 
        else: 
            status_item.setForeground(QColor(Qt.GlobalColor.darkGray)) 
        
        self.file_table.setItem(row, 5, status_item)

        # Column 6: Original Token Count (Yeni)
        original_token_item = QTableWidgetItem(str(entry_data["original_token_count"]))
        if isinstance(entry_data["original_token_count"], str) and "Hesaplanmadı" in entry_data["original_token_count"]:
            original_token_item.setForeground(QColor(Qt.GlobalColor.blue)) # Henüz hesaplanmadıysa mavi
        self.file_table.setItem(row, 6, original_token_item)
        
        # Column 7: Translated Token Count (Yeni)
        translated_token_item = QTableWidgetItem(str(entry_data["translated_token_count"]))
        if isinstance(entry_data["translated_token_count"], str) and ("Hesaplanmadı" in entry_data["translated_token_count"] or "Yok" in entry_data["translated_token_count"]):
            translated_token_item.setForeground(QColor(Qt.GlobalColor.blue)) # Henüz hesaplanmadıysa/yoksa mavi
        self.file_table.setItem(row, 7, translated_token_item)

    def start_token_counting_manually(self):
        """Token sayma işlemini buton aracılığıyla başlatır."""
        self._start_token_counting()

    def _start_token_counting(self):
        """Token sayma işlemini arka planda başlatır."""
        if not self.current_project_path:
            QMessageBox.warning(self, "Proje Seçilmedi", "Token saymak için lütfen önce bir proje seçin.")
            return

        # Önceki token sayma işlemi tamamlanmamışsa durdur
        if self.token_count_thread and self.token_count_thread.isRunning():
            self.token_count_worker.stop()
            self.token_count_thread.quit()
            self.token_count_thread.wait(1000) 
            self.token_count_thread = None
            self.token_count_worker = None

        config_path = os.path.join(self.current_project_path, 'config', 'config.ini')
        api_key = ""
        if os.path.exists(config_path):
            try:
                self.config.read(config_path)
                api_key = self.config.get('API', 'gemini_api_key', fallback="")
            except configparser.Error:
                api_key = "" # Hata olursa anahtar boş kalsın
        
        if not api_key:
            QMessageBox.warning(self, "API Anahtarı Eksik", "Token sayımı için Gemini API anahtarı gereklidir. Lütfen proje ayarlarına girerek API anahtarınızı tanımlayın.")
            self.total_tokens_label.setText("Toplam Token: API Anahtarı Yok")
            self.total_original_tokens_label.setText("Orijinal Token: API Anahtarı Yok")
            self.total_translated_tokens_label.setText("Çevrilen Token: API Anahtarı Yok")
            self.token_progress_bar.setVisible(False)
            self.total_tokens_label.setVisible(True)
            self.total_original_tokens_label.setVisible(True)
            self.total_translated_tokens_label.setVisible(True)
            return

        # Diğer butonları devre dışı bırak
        self.startButton.setEnabled(False)
        self.translateButton.setEnabled(False)
        self.cleanButton.setEnabled(False)
        self.mergeButton.setEnabled(False)
        self.chapterCheckButton.setEnabled(False)
        self.projectSettingsButton.setEnabled(False)
        self.selectHighlightedButton.setEnabled(False)
        self.token_count_button.setEnabled(False) # Kendi butonunu da devre dışı bırak
        self.token_count_button.setText("Sayılıyor...")
        self.token_count_button.setStyleSheet("background-color: #FFC107; color: black; border-radius: 5px; padding: 10px;")

        self.token_progress_bar.setValue(0)
        self.token_progress_bar.setMaximum(0) 
        self.token_progress_bar.setVisible(True)
        self.statusLabel.setText("Durum: Token'lar hesaplanıyor...")
        self.total_tokens_label.setText("Toplam Token: Hesaplıyor...")
        self.total_original_tokens_label.setText("Orijinal Token: Hesaplıyor...")
        self.total_translated_tokens_label.setText("Çevrilen Token: Hesaplıyor...")
        self.total_tokens_label.setVisible(True)
        self.total_original_tokens_label.setVisible(True)
        self.total_translated_tokens_label.setVisible(True)

        self.token_count_thread = QThread()
        # Worker'a mevcut önbelleği gönderiyoruz
        self.token_count_worker = TokenCountWorker(self.current_project_path, api_key, self.project_token_cache)
        self.token_count_worker.moveToThread(self.token_count_thread)

        self.token_count_thread.started.connect(self.token_count_worker.run)
        self.token_count_worker.finished.connect(self.token_count_thread.quit)
        self.token_count_worker.finished.connect(self.token_count_worker.deleteLater)
        self.token_count_thread.finished.connect(self.token_count_thread.deleteLater)
        
        self.token_count_worker.finished.connect(self._on_token_counting_finished)
        self.token_count_worker.progress.connect(self._update_token_counting_progress)
        self.token_count_worker.error.connect(self._on_token_counting_error)

        self.token_count_thread.start()

    def _update_token_counting_progress(self, current, total):
        self.token_progress_bar.setMaximum(total)
        self.token_progress_bar.setValue(current)
        self.statusLabel.setText(f"Durum: Token sayılıyor... Dosya {current}/{total}")

    def _on_token_counting_finished(self, results):
        self.statusLabel.setText("Durum: Token sayımı tamamlandı.")
        self.token_progress_bar.setVisible(False)
        self.token_count_button.setText("Token Say")
        self.token_count_button.setStyleSheet("background-color: #673AB7; color: white; border-radius: 5px; padding: 10px;") # Rengi geri yükle
        self._set_all_buttons_enabled_state(True) # Diğer butonları tekrar aktif et

        # Önbelleği güncelleyelim
        self.project_token_cache = results
        # Güncellenmiş önbelleği dosyaya kaydedelim
        config_folder_path = os.path.join(self.current_project_path, 'config')
        save_token_data(config_folder_path, self.project_token_cache)


        file_tokens = results['file_token_data']
        total_original = results['total_original_tokens']
        total_translated = results['total_translated_tokens']
        total_combined = results['total_combined_tokens']

        # Her bir dosyanın token sayısını tabloya işle
        for row in range(self.file_table.rowCount()):
            original_file_name = self.file_table.item(row, 1).text()
            translated_file_name = self.file_table.item(row, 2).text()
            status_text = self.file_table.item(row, 5).text() 

            original_token_str = "Yok"
            translated_token_str = "Yok"
            
            # Orijinal dosya adına göre token bilgisini arayalım
            if original_file_name != "Orijinali Yok" and original_file_name != "N/A" and original_file_name in file_tokens:
                original_token_val = file_tokens[original_file_name].get("original_tokens")
                original_token_str = str(original_token_val) if original_token_val is not None else "Hata/N/A"
            
            # Çevrilen veya birleştirilmiş dosya adına göre token bilgisini arayalım
            if translated_file_name != "Yok" and translated_file_name != "N/A" and translated_file_name in file_tokens:
                if "Birleştirildi" in status_text: 
                    translated_token_val = file_tokens[translated_file_name].get("merged_tokens")
                else: 
                    translated_token_val = file_tokens[translated_file_name].get("translated_tokens")
                
                translated_token_str = str(translated_token_val) if translated_token_val is not None else "Hata/Yok"

            original_token_item = QTableWidgetItem(original_token_str)
            translated_token_item = QTableWidgetItem(translated_token_str)

            # Hata veya N/A durumlarında kırmızı renklendirme
            if "Hata" in original_token_str or original_token_str == "N/A":
                original_token_item.setForeground(QColor(Qt.GlobalColor.red))
            if "Hata" in translated_token_str or translated_token_str == "Yok" or translated_token_str == "N/A":
                translated_token_item.setForeground(QColor(Qt.GlobalColor.red))
                
            self.file_table.setItem(row, 6, original_token_item)
            self.file_table.setItem(row, 7, translated_token_item)

        # Genel token bilgilerini güncelle
        self.total_tokens_label.setText(f"Toplam Token (Orijinal + Çevrilen): {total_combined}")
        self.total_original_tokens_label.setText(f"Toplam Orijinal Token: {total_original}")
        self.total_translated_tokens_label.setText(f"Toplam Çevrilen Token: {total_translated}")
        self.total_tokens_label.setVisible(True)
        self.total_original_tokens_label.setVisible(True)
        self.total_translated_tokens_label.setVisible(True)

    def _on_token_counting_error(self, message):
        QMessageBox.critical(self, "Token Sayım Hatası", f"Token sayımı sırasında bir hata oluştu:\n{message}")
        self.statusLabel.setText(f"Durum: Token sayım hatası - {message}")
        self.token_progress_bar.setVisible(False)
        self.token_count_button.setText("Token Say")
        self.token_count_button.setStyleSheet("background-color: #673AB7; color: white; border-radius: 5px; padding: 10px;") # Rengi geri yükle
        self._set_all_buttons_enabled_state(True) # Diğer butonları tekrar aktif et

        self.total_tokens_label.setText("Toplam Token: Hata")
        self.total_original_tokens_label.setText("Orijinal Token: Hata")
        self.total_translated_tokens_label.setText("Çevrilen Token: Hata")
        self.total_tokens_label.setVisible(True)
        self.total_original_tokens_label.setVisible(True)
        self.total_translated_tokens_label.setVisible(True)

    def _set_all_buttons_enabled_state(self, enabled):
        """Tüm ana işlem butonlarının etkinliğini ayarlar."""
        self.startButton.setEnabled(enabled)
        self.translateButton.setEnabled(enabled)
        self.cleanButton.setEnabled(enabled)
        self.mergeButton.setEnabled(enabled)
        self.chapterCheckButton.setEnabled(enabled)
        self.projectSettingsButton.setEnabled(enabled)
        self.selectHighlightedButton.setEnabled(enabled)
        self.token_count_button.setEnabled(enabled)


    def add_file_to_table(self, file_path, file_name):
        pass 

    def save_settings_clicked(self):
        QMessageBox.information(self, "Kaydet", "Uygulama ayarları (genel) buraya kaydedilecektir. Proje ayarları için 'Proje Ayarları' butonunu kullanın.")
        print("'Ayarları Kaydet' tıklandı.")
        

    def open_project_settings_dialog(self):
        current_item = self.project_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Proje Seçilmedi", "Lütfen ayarlarını düzenlemek istediğiniz bir proje seçin.")
            return

        project_name = current_item.text()
        project_path = os.path.join(os.getcwd(), project_name)
        config_path = os.path.join(project_path, 'config', 'config.ini')

        project_link = ""
        max_pages = None
        api_key = ""  # Varsayılan API anahtarı
        startpromt = ""
        

        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.config.read_file(f)
                project_link = self.config.get('ProjectInfo', 'link', fallback="")
                max_pages = self.config.getint('ProjectInfo', 'max_pages', fallback=None)
                api_key = self.config.get('API', 'gemini_api_key', fallback="")

                startpromt = self.config.get('Startpromt', 'startpromt', fallback="")
            except: pass

        dialog = ProjectSettingsDialog(project_name, project_link, max_pages, api_key, startpromt, self)
        if dialog.exec():
            updated_data = dialog.get_data()
            try:
                self.config['ProjectInfo']['link'] = updated_data['link']
                if updated_data['max_pages']: self.config['ProjectInfo']['max_pages'] = str(updated_data['max_pages'])
                else: 
                     if 'max_pages' in self.config['ProjectInfo']: del self.config['ProjectInfo']['max_pages']
                     
                
                self.config['API']['gemini_api_key'] = updated_data['api_key']
                self.config['Startpromt']['startpromt'] = updated_data['Startpromt']  # Yeni başlangıç istemi
                with open(config_path, 'w', encoding='utf-8') as configfile:
                    self.config.write(configfile)
                QMessageBox.information(self, "Ayarlar Kaydedildi", f"'{project_name}' projesinin ayarları başarıyla kaydedildi.")
                self.update_file_list_from_selection() 
            except Exception as e:
                QMessageBox.critical(self, "Kaydetme Hatası", f"Ayarlar kaydedilirken bir hata oluştu:\n{e}")

    def show_help_clicked(self):
        """Yardım bilgilerini gösterme işlevi."""
        QMessageBox.information(self, "Yardım", "Uygulama ile ilgili yardım bilgileri buraya gelecek.")
        print("'Yardım' tıklandı.")

    def show_about_dialog(self):
        """Hakkında iletişim kutusunu gösterme işlevi."""
        QMessageBox.about(self, "Hakkında", 
                          "NovelAlem Çeviri Aracı.\n\n"
                          "Bu uygulama UtkuCanC tarafından NovelAlem için webnovel çevirilerini yapay zeka desteği ile çevirisininin yapılması amacıyla geliştirilmiştir.\n\n"
                          "Sürüm: 1.9 (	Model değişikliği: gemini-2.5-flash-preview-09-2025.)\n"
                          "Sürüm: 1.9.1 (Gemini model değiştirme ve seçme özelliği eklendi)\n"
                          "Sürüm: 1.9.2 (API ve Promt hafızası eklendi. Ekleme, seçim ve düzenleme paneli eklendi.)\n"
                          "Sürüm: 1.9.3 (Bölüm başlığı kontrolü getirildi.)\n\n"
                          "Geliştirici: UtkuCanC\n"
                          "2025\n")

    def table_key_press_event(self, event):
        """QTableWidget'ta Enter tuşuna basıldığında vurgulanan satırları işaretler."""
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            self.mark_highlighted_rows_checked()
        else:
            QTableWidget.keyPressEvent(self.file_table, event)

    def mark_highlighted_rows_checked(self):
        """Tabloda vurgulanan satırların onay kutularını işaretler."""
        selected_rows = set()
        for item in self.file_table.selectedItems():
            selected_rows.add(item.row())
        
        for row in selected_rows:
            checkbox_item = self.file_table.item(row, 0)
            if checkbox_item:
                checkbox_item.setCheckState(Qt.CheckState.Checked)

    def file_table_context_menu(self, position):
        """Dosya tablosu için sağ tıklama menüsünü oluşturur ve görüntüler."""
        # Tıklanan hücrenin indeksini al
        index = self.file_table.indexAt(position)
        if not index.isValid():
            return

        row = index.row()
        column = index.column() # Tıklanan sütun indeksi

        menu = QMenu(self)

        # "Dosyayı Aç" eylemi - tıklanan sütuna göre dosya seçimi
        open_file_action = QAction("Dosyayı Aç", self)
        open_file_action.triggered.connect(lambda: self.open_selected_file(row, column))
        menu.addAction(open_file_action)

        # "Klasörü Aç" eylemi - tıklanan sütuna göre klasör seçimi
        open_folder_action = QAction("Klasörü Aç", self)
        open_folder_action.triggered.connect(lambda: self.open_selected_folder(row, column))
        menu.addAction(open_folder_action)

        menu.exec(self.file_table.viewport().mapToGlobal(position))

    def open_selected_file(self, row, clicked_column):
        """Seçili dosyayı varsayılan programıyla açar."""
        if not self.current_project_path:
            QMessageBox.warning(self, "Hata", "Lütfen önce bir proje seçin.")
            return

        original_file_name = self.file_table.item(row, 1).text()
        translated_file_name = self.file_table.item(row, 2).text()
        status = self.file_table.item(row, 5).text()

        file_path_to_open = None

        # Tıklanan sütuna göre öncelik ver
        if clicked_column == 1 or clicked_column == 6: # Orijinal dosya veya Orijinal Token sütunu
            if original_file_name and original_file_name != "Orijinali Yok" and original_file_name != "N/A":
                file_path_to_open = os.path.join(self.current_project_path, 'dwnld', original_file_name)
        elif clicked_column == 2 or clicked_column == 7: # Çevrilen dosya veya Çevrilen Token sütunu
            if status == "Birleştirildi":
                if translated_file_name and translated_file_name != "Yok":
                    file_path_to_open = os.path.join(self.current_project_path, 'cmplt', translated_file_name)
            elif translated_file_name and translated_file_name != "Yok":
                file_path_to_open = os.path.join(self.current_project_path, 'trslt', translated_file_name)
        else: # Diğer sütunlar için mevcut mantık
            if status == "Birleştirildi":
                if translated_file_name and translated_file_name != "Yok":
                    file_path_to_open = os.path.join(self.current_project_path, 'cmplt', translated_file_name)
            elif translated_file_name and translated_file_name != "Yok" and ("Çevrildi" in status or status.startswith("Hata:") or "Temizlenmedi" in status or "Temizlendi" in status):
                file_path_to_open = os.path.join(self.current_project_path, 'trslt', translated_file_name)
            elif original_file_name and original_file_name != "Orijinali Yok" and ("İndirildi" in status or status.startswith("Hata:")):
                file_path_to_open = os.path.join(self.current_project_path, 'dwnld', original_file_name)
        
        if file_path_to_open and os.path.exists(file_path_to_open):
            try:
                if sys.platform == "win32":
                    os.startfile(file_path_to_open)
                elif sys.platform == "darwin": 
                    subprocess.run(["open", file_path_to_open])
                else: 
                    subprocess.run(["xdg-open", file_path_to_open])
            except Exception as e:
                QMessageBox.critical(self, "Dosya Açma Hatası", f"Dosya açılamadı:\n{e}")
        else:
            QMessageBox.warning(self, "Dosya Bulunamadı", "Seçilen dosyanın yolu mevcut değil veya dosya bulunamadı.")


    def open_selected_folder(self, row, clicked_column):
        """Seçili dosyayı içeren klasörü açar."""
        if not self.current_project_path:
            QMessageBox.warning(self, "Hata", "Lütfen önce bir proje seçin.")
            return
            
        original_file_name = self.file_table.item(row, 1).text()
        translated_file_name = self.file_table.item(row, 2).text()
        status = self.file_table.item(row, 5).text()

        folder_path_to_open = None

        # Tıklanan sütuna göre klasör seçimi
        if clicked_column == 1 or clicked_column == 6: # Orijinal dosya veya Orijinal Token sütunu
            if original_file_name and original_file_name != "Orijinali Yok" and original_file_name != "N/A":
                folder_path_to_open = os.path.join(self.current_project_path, 'dwnld')
        elif clicked_column == 2 or clicked_column == 7: # Çevrilen dosya veya Çevrilen Token sütunu
            if status == "Birleştirildi":
                if translated_file_name and translated_file_name != "Yok":
                    folder_path_to_open = os.path.join(self.current_project_path, 'cmplt')
            elif translated_file_name and translated_file_name != "Yok":
                folder_path_to_open = os.path.join(self.current_project_path, 'trslt')
        else: # Diğer sütunlar için mevcut mantık
            if status == "Birleştirildi":
                if translated_file_name and translated_file_name != "Yok":
                    folder_path_to_open = os.path.join(self.current_project_path, 'cmplt')
            elif translated_file_name and translated_file_name != "Yok" and ("Çevrildi" in status or status.startswith("Hata:")):
                folder_path_to_open = os.path.join(self.current_project_path, 'trslt')
            elif original_file_name and original_file_name != "Orijinali Yok" and ("İndirildi" in status or status.startswith("Hata:")):
                folder_path_to_open = os.path.join(self.current_project_path, 'dwnld')


        if folder_path_to_open and os.path.exists(folder_path_to_open):
            try:
                if sys.platform == "win32":
                    os.startfile(folder_path_to_open)
                elif sys.platform == "darwin": 
                    subprocess.run(["open", folder_path_to_open])
                else: 
                    subprocess.run(["xdg-open", folder_path_to_open])
            except Exception as e:
                QMessageBox.critical(self, "Klasör Açma Hatası", f"Klasör açılamadı:\n{e}")
        else:
            QMessageBox.warning(self, "Klasör Bulunamadı", "Seçilen dosyanın klasör yolu mevcut değil veya klasör bulunamadı.")


    def closeEvent(self, event):
        """Uygulama kapatılırken çalışan tüm indirme veya çevirme işlemlerini durdurur."""
        running_threads = []
        if self.download_thread and self.download_thread.isRunning():
            running_threads.append(self.download_worker)
        if self.translation_thread and self.translation_thread.isRunning():
            running_threads.append(self.translation_worker)
        if self.cleaning_thread and self.cleaning_thread.isRunning():
            running_threads.append(self.cleaning_worker)
        if self.merging_thread and self.merging_thread.isRunning():
            running_threads.append(self.merging_worker)
        if self.token_count_thread and self.token_count_thread.isRunning(): 
            running_threads.append(self.token_count_worker)
        if self.chapter_check_thread and self.chapter_check_thread.isRunning(): # Yeni thread
            running_threads.append(self.chapter_check_worker)

        if running_threads:
            reply = QMessageBox.question(self, 'Uygulamayı Kapat', 
                                         "Devam eden işlemler var. Çıkmak istediğinizden emin misiniz? Tüm işlemler durdurulacaktır.",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                         QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                for worker in running_threads:
                    worker.stop()
                
                for _ in range(5): 
                    all_stopped = True
                    if self.download_thread and self.download_thread.isRunning(): all_stopped = False
                    if self.translation_thread and self.translation_thread.isRunning(): all_stopped = False
                    if self.cleaning_thread and self.cleaning_thread.isRunning(): all_stopped = False
                    if self.merging_thread and self.merging_thread.isRunning(): all_stopped = False
                    if self.token_count_thread and self.token_count_thread.isRunning(): all_stopped = False
                    if self.chapter_check_thread and self.chapter_check_thread.isRunning(): all_stopped = False # Yeni thread

                    if all_stopped:
                        break
                    time.sleep(1) 

                if not all_stopped:
                    print("Uyarı: Bazı iş parçacıkları hala çalışıyor. Zorla sonlandırılıyor.")
                    sys.exit() 
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())