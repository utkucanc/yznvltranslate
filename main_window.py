import sys
import os
import configparser
import time
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QListWidget,
    QTableWidget, QTableWidgetItem, QHBoxLayout,
    QVBoxLayout, QHeaderView, QSizePolicy, QLineEdit,
    QMessageBox, QPushButton, QLabel, QFrame
)
from PyQt6.QtGui import QFont, QIcon, QDesktopServices
from PyQt6.QtCore import Qt, QUrl, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtWidgets import QGraphicsOpacityEffect
from core.localization import tr

# Kendi oluşturduğumuz modülleri içe aktarıyoruz
from dialogs import (
    NewProjectDialog, ProjectSettingsDialog, PromptEditorDialog,
    ApiKeyEditorDialog, GeminiVersionDialog, MCPServerDialog,
    TerminologyDialog, SeleniumMenuDialog
)
from core.workers.token_counter import load_token_data, save_token_data
from logger import app_logger
from ui.request_counter_manager import RequestCounterManager
from ui.app_settings_dialog import AppSettingsDialog, load_app_settings, apply_theme
from ui.menu_bar_builder import build_menu_bar
from ui.right_panel_builder import build_right_panel
from ui.status_bar_manager import StatusBarManager
from ui.file_table_interactions import FileTableInteractions
from ui.api_stats_dialog import show_api_stats_dialog
from core.download_controller import DownloadController
from core.translation_controller import TranslationController
from core.merge_controller import MergeController
from core.token_controller import TokenController
from core.process_controller import (
    CleaningController, SplitController, EpubController,
    ErrorCheckController, ChapterCheckController, MLTerminologyController
)
from ui.toast_widget import _ToastWidget





class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("main_window.title", "Novel Çeviri Aracı V2.4.0"))
        self.setWindowIcon(QIcon("logo256.ico"))
        self.setGeometry(100, 100, 1400, 800)

        # İstatistikler (status bar için)
        self.request_counter_manager = RequestCounterManager()
        self._api_token_count = 0
        self._translation_speed = 0.0
        self._current_model = self.get_gemini_model_version()
        self._current_api_name = ""
        self._current_status = tr("right_panel.status_ready", "Hazır")
        self._ensure_app_structure()
        self.current_project_path = None
        self.config = configparser.ConfigParser()
        self.project_token_cache = {}

        # Controller'ları oluştur
        self.download_ctrl = DownloadController(self)
        self.translation_ctrl = TranslationController(self)
        self.merge_ctrl = MergeController(self)
        self.token_ctrl = TokenController(self)
        self.cleaning_ctrl = CleaningController(self)
        self.split_ctrl = SplitController(self)
        self.epub_ctrl = EpubController(self)
        self.error_check_ctrl = ErrorCheckController(self)
        self.chapter_check_ctrl = ChapterCheckController(self)
        self.ml_terminology_ctrl = MLTerminologyController(self)

        # UI oluştur
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.outer_layout = QVBoxLayout(self.central_widget)
        self.main_layout = QHBoxLayout()
        self.outer_layout.addLayout(self.main_layout, 1)

        # FileTableInteractions erken oluşturulmalı (paneller referans ediyor)
        self.file_table_interactions = FileTableInteractions(self)

        build_menu_bar(self)
        self._create_left_panel()
        self._create_center_panel()
        build_right_panel(self)

        # Tablo etkileşimlerini bağla (file_table artık mevcut)
        self.file_table_interactions.setup()

        self.status_bar_mgr = StatusBarManager(self)
        self.status_bar_mgr.create()

        self.load_existing_projects()

        # Başlangıç durumları
        self.total_tokens_label.setVisible(False)
        self.total_original_tokens_label.setVisible(False)
        self.total_translated_tokens_label.setVisible(False)
        self.token_progress_bar.setVisible(False)
        self.token_count_button.setEnabled(False)

        # Tema uygula
        app_settings = load_app_settings()
        apply_theme(QApplication.instance(), app_settings.get("theme", "dark"))

        # Sistem tray
        self._tray_icon = None
        self._setup_tray_icon()

    # Uygulama Yapısı
    def _ensure_app_structure(self):
        base_path = os.getcwd()
        paths = [
            os.path.join(base_path, "AppConfigs"),
            os.path.join(base_path, "AppConfigs", "Promts"),
            os.path.join(base_path, "AppConfigs", "APIKeys"),
            os.path.join(base_path, "AppConfigs", "APIKeys", "MCP"),
            os.path.join(base_path, "AppConfigs", "themes"),
        ]
        try:
            for p in paths:
                if not os.path.exists(p):
                    os.makedirs(p)
        except Exception as e:
            QMessageBox.critical(self, tr("main_window.msg_structure_error_title", "Hata"), tr("main_window.msg_structure_error_body", "Klasör yapısı oluşturulamadı: {}").format(e))
        # Varsayılan tema dosyalarını oluştur (build'de eksik olabilir)
        try:
            from core.theme_defaultCreate import ensure_default_themes
            ensure_default_themes(base_path)
        except Exception as e:
            app_logger.warning(f"Tema dosyaları oluşturulamadı: {e}")
        mcp_file = os.path.join(base_path, "AppConfigs", "MCP_Endpoints.json")
        if not os.path.exists(mcp_file):
            try:
                from core.llm_provider import save_endpoints, DEFAULT_ENDPOINTS
                save_endpoints(DEFAULT_ENDPOINTS)
            except Exception:
                pass

    def get_gemini_model_version(self):
        base_path = os.getcwd()
        config_path = os.path.join(base_path, "AppConfigs", "GVersion.ini")
        config = configparser.ConfigParser()
        if os.path.exists(config_path):
            config.read(config_path)
            return config.get("Version", "model_name", fallback="gemini-2.5-flash")
        return "gemini-2.5-flash"

    # Panel Oluşturma 
    def _create_left_panel(self):
        left_layout = QVBoxLayout()
        self.projects_label = QLabel(tr("main_window.projects", "Projeler:"))
        left_layout.addWidget(self.projects_label)
        search_layout = QHBoxLayout()
        search_layout.setSpacing(4)
        self.project_search_input = QLineEdit()
        self.project_search_input.setPlaceholderText(tr("main_window.search_project_placeholder", "🔍 Proje ara..."))
        self.project_search_input.textChanged.connect(self.file_table_interactions.filter_project_list)
        self.project_search_clear_btn = QPushButton("✕")
        self.project_search_clear_btn.setProperty("class", "btn-clear")
        self.project_search_clear_btn.setFixedSize(22, 22)
        self.project_search_clear_btn.setToolTip(tr("main_window.tooltip_clear_search", "Aramayı temizle"))
        self.project_search_clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.project_search_clear_btn.clicked.connect(lambda: self.project_search_input.clear())
        search_layout.addWidget(self.project_search_input)
        search_layout.addWidget(self.project_search_clear_btn)
        left_layout.addLayout(search_layout)
        self.project_list = QListWidget()
        self.project_list.setFont(QFont("Segoe UI", 9))
        self.project_list.currentItemChanged.connect(self.update_file_list_from_selection)
        self.project_list.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Expanding)
        self.project_list.setMaximumWidth(220)
        left_layout.addWidget(self.project_list)
        self.main_layout.addLayout(left_layout, 1)

    def _create_center_panel(self):
        center_layout = QVBoxLayout()
        file_search_layout = QHBoxLayout()
        file_search_layout.setSpacing(4)
        self.file_search_input = QLineEdit()
        self.file_search_input.setPlaceholderText(tr("main_window.search_file_placeholder", "🔍 Dosya ara..."))
        self.file_search_input.textChanged.connect(self.file_table_interactions.filter_file_table)
        self.file_search_clear_btn = QPushButton("✕")
        self.file_search_clear_btn.setProperty("class", "btn-clear")
        self.file_search_clear_btn.setFixedSize(22, 22)
        self.file_search_clear_btn.setToolTip(tr("main_window.tooltip_clear_file_search", "Dosya aramasını temizle"))
        self.file_search_clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.file_search_clear_btn.clicked.connect(lambda: self.file_search_input.clear())
        file_search_layout.addWidget(self.file_search_input)
        file_search_layout.addWidget(self.file_search_clear_btn)
        center_layout.addLayout(file_search_layout)
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(8)
        # Kısaltılmış başlıklar - dar sütunlarda okunabilirlik için
        headers = [
            tr("main_window.table_header_check", "☑"),
            tr("main_window.table_header_original", "Orijinal"),
            tr("main_window.table_header_translated", "Çevrilen"),
            tr("main_window.table_header_date", "Tarih"),
            tr("main_window.table_header_size", "Boyut"),
            tr("main_window.table_header_status", "Durum"),
            tr("main_window.table_header_orig_token", "Orig.Token"),
            tr("main_window.table_header_trsl_token", "Trsl.Token")
        ]
        self.file_table.setHorizontalHeaderLabels(headers)
        self.file_table.horizontalHeader().setFont(QFont("Segoe UI", 8))
        self.file_table.horizontalHeader().setDefaultSectionSize(80)
        for i, mode in enumerate([
            QHeaderView.ResizeMode.ResizeToContents,
            QHeaderView.ResizeMode.Stretch,
            QHeaderView.ResizeMode.Stretch,
            QHeaderView.ResizeMode.ResizeToContents,
            QHeaderView.ResizeMode.ResizeToContents,
            QHeaderView.ResizeMode.ResizeToContents,
            QHeaderView.ResizeMode.ResizeToContents,
            QHeaderView.ResizeMode.ResizeToContents,
        ]):
            self.file_table.horizontalHeader().setSectionResizeMode(i, mode)
        self.file_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.file_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.file_table.setAlternatingRowColors(True)
        self.file_table.verticalHeader().setDefaultSectionSize(26)  # 10pt font ile uyumlu satır yüksekliği
        self.file_table.verticalHeader().setVisible(True)  
        center_layout.addWidget(self.file_table)
        self.main_layout.addLayout(center_layout, 4)

    # Controller'lara yönlendirme (butonlar bu metotlara bağlı)
    def start_download_process(self):
        self.download_ctrl.start()

    def start_split_process(self):
        self.split_ctrl.start()

    def start_translation_process(self):
        self.translation_ctrl.start()

    def stop_translation_process(self):
        self.translation_ctrl.stop_translation()

    def start_merging_process(self):
        self.merge_ctrl.start()

    def start_cleaning_process(self):
        self.cleaning_ctrl.start()

    def start_epub_process(self):
        self.epub_ctrl.start()

    def start_error_check_process(self):
        self.error_check_ctrl.start()

    def start_chapter_check_process(self):
        self.chapter_check_ctrl.start()

    def start_ml_terminology_process(self):
        self.ml_terminology_ctrl.start()

    def start_token_counting_manually(self):
        self.token_ctrl.start()

    def mark_highlighted_rows_checked(self):
        self.file_table_interactions.mark_highlighted_rows_checked()

    def show_api_stats_dialog(self):
        show_api_stats_dialog(self)

    # Diyalog Açma
    def open_prompt_editor(self):
        PromptEditorDialog(self).exec()

    def open_apikey_editor(self):
        ApiKeyEditorDialog(self).exec()

    def open_gemini_version_dialog(self):
        GeminiVersionDialog(self).exec()

    def open_mcp_dialog(self):
        MCPServerDialog(self).exec()

    def open_app_settings_dialog(self):
        dialog = AppSettingsDialog(self)
        dialog.settings_changed.connect(self._on_app_settings_changed)
        dialog.exec()

    def open_theme_manager_dialog(self):
        from ui.theme_manager_dialog import ThemeManagerDialog
        current = load_app_settings().get("theme", "dark")
        dlg = ThemeManagerDialog(current_theme=current, parent=self)
        dlg.theme_applied.connect(self._on_theme_manager_default_changed)
        dlg.exec()

    def _on_theme_manager_default_changed(self, theme_name: str):
        """Tema yöneticisinden varsayılan tema değiştiğinde anında uygula."""
        apply_theme(QApplication.instance(), theme_name)
        app_logger.info(f"Tema Yöneticisinden tema uygulandı: {theme_name}")

    def _on_app_settings_changed(self, settings: dict):
        apply_theme(QApplication.instance(), settings.get("theme", "dark"))
        app_logger.info("Uygulama ayarları güncellendi.")

    # Proje Yönetimi
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
            project_name, project_link, max_pages, max_retries, api_key, startpromt, api_key_name, mcp_endpoint_id = dialog.get_data()
            if not project_name or not project_link:
                QMessageBox.warning(self, tr("main_window.msg_project_missing_info_title", "Eksik Bilgi"), tr("main_window.msg_project_missing_info_body", "Proje adı ve linki boş bırakılamaz."))
                return
            if not api_key and not mcp_endpoint_id:
                QMessageBox.warning(self, tr("main_window.msg_project_config_missing_title", "Yapılandırma Eksik"), tr("main_window.msg_project_config_missing_body", "Çeviri ve token sayımı için Gemini API anahtarı veya MCP bağlantısı gereklidir."))
            try:
                base_path = os.path.join(os.getcwd(), project_name)
                if os.path.exists(base_path):
                    QMessageBox.warning(self, tr("main_window.msg_project_exists_title", "Hata"), tr("main_window.msg_project_exists_body", "'{}' adında bir proje zaten mevcut.").format(project_name))
                    return
                for folder in ["dwnld", "trslt", "cmplt", "config"]:
                    os.makedirs(os.path.join(base_path, folder))
                self.config['ProjectInfo'] = {'link': project_link}
                if max_pages is not None:
                    self.config['ProjectInfo']['max_pages'] = str(max_pages)
                self.config['ProjectInfo']['max_retries'] = str(max_retries)
                self.config['API'] = {'gemini_api_key': api_key, 'api_key_name': api_key_name}
                self.config["Startpromt"] = {'startpromt': startpromt}
                if mcp_endpoint_id:
                    self.config['MCP'] = {'endpoint_id': mcp_endpoint_id}
                elif 'MCP' in self.config:
                    del self.config['MCP']
                config_path = os.path.join(base_path, 'config', 'config.ini')
                with open(config_path, 'w', encoding='utf-8') as configfile:
                    self.config.write(configfile)
                self.project_list.addItem(project_name)
                QMessageBox.information(self, tr("main_window.msg_project_created_title", "Başarılı"), tr("main_window.msg_project_created_body", "'{}' projesi başarıyla oluşturuldu.").format(project_name))
                self.project_list.setCurrentItem(self.project_list.findItems(project_name, Qt.MatchFlag.MatchExactly)[0])
            except OSError as e:
                QMessageBox.critical(self, tr("main_window.msg_folder_error_title", "Dosya Hatası"), tr("main_window.msg_folder_error_body", "Dizin oluşturulurken bir hata oluştu:\n{}").format(e))
            except Exception as e:
                QMessageBox.critical(self, tr("main_window.msg_generic_error_title", "Genel Hata"), tr("main_window.msg_generic_error_body", "Proje oluşturulurken beklenmeyen bir hata oluştu:\n{}").format(e))

    def delete_project_clicked(self):
        import shutil
        current_item = self.project_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, tr("main_window.msg_project_not_selected_title", "Proje Seçilmedi"), tr("main_window.msg_project_not_selected_body", "Lütfen silmek istediğiniz projeyi seçin."))
            return
        project_name = current_item.text()
        reply = QMessageBox.question(self, tr("main_window.msg_delete_project_confirm_title", "Proje Sil"),
                                     tr("main_window.msg_delete_project_confirm_body", "'{}' projesini ve tüm içeriğini silmek istediğinize emin misiniz? Bu işlem geri alınamaz.").format(project_name),
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            project_path = os.path.join(os.getcwd(), project_name)
            try:
                shutil.rmtree(project_path)
                self.project_list.takeItem(self.project_list.row(current_item))
                QMessageBox.information(self, tr("main_window.msg_delete_project_success_title", "Başarılı"), tr("main_window.msg_delete_project_success_body", "'{}' projesi başarıyla silindi.").format(project_name))
                self.update_file_list_from_selection()
            except Exception as e:
                QMessageBox.critical(self, tr("main_window.msg_delete_project_error_title", "Silme Hatası"), tr("main_window.msg_delete_project_error_body", "Proje silinirken bir hata oluştu:\n{}").format(e))

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
        max_retries = 3
        api_key = ""
        startpromt = ""
        gemini_version = self.get_gemini_model_version()
        mcp_endpoint_id = None
        cache_enabled = False
        terminology_enabled = True
        async_enabled = False
        async_threads = 3
        batch_enabled = False
        max_batch_chars = 33000
        max_chapters_per_batch = 3
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.config.read_file(f)
                project_link = self.config.get('ProjectInfo', 'link', fallback="")
                max_pages = self.config.getint('ProjectInfo', 'max_pages', fallback=None)
                max_retries = self.config.getint('ProjectInfo', 'max_retries', fallback=3)
                api_key = self.config.get('API', 'gemini_api_key', fallback="")
                startpromt = self.config.get('Startpromt', 'startpromt', fallback="")
                mcp_endpoint_id = self.config.get('MCP', 'endpoint_id', fallback=None)
                cache_enabled = self.config.getboolean('Features', 'cache_enabled', fallback=False)
                terminology_enabled = self.config.getboolean('Features', 'terminology_enabled', fallback=True)
                async_enabled = self.config.getboolean('Features', 'async_enabled', fallback=False)
                async_threads = self.config.getint('Features', 'async_threads', fallback=3)
                batch_enabled = self.config.getboolean('Batch', 'batch_enabled', fallback=False)
                max_batch_chars = self.config.getint('Batch', 'max_batch_chars', fallback=33000)
                max_chapters_per_batch = self.config.getint('Batch', 'max_chapters_per_batch', fallback=3)
            except Exception:
                pass
        self.max_retries = max_retries
        dialog = ProjectSettingsDialog(
            project_name, project_link, max_pages, api_key, startpromt, gemini_version, self,
            mcp_endpoint_id=mcp_endpoint_id, cache_enabled=cache_enabled,
            terminology_enabled=terminology_enabled, async_enabled=async_enabled,
            async_threads=async_threads, batch_enabled=batch_enabled,
            max_batch_chars=max_batch_chars, max_chapters_per_batch=max_chapters_per_batch,
        )
        if dialog.exec():
            updated_data = dialog.get_data()
            try:
                if 'ProjectInfo' not in self.config:
                    self.config['ProjectInfo'] = {}
                self.config['ProjectInfo']['link'] = updated_data['link']
                if updated_data['max_pages']:
                    self.config['ProjectInfo']['max_pages'] = str(updated_data['max_pages'])
                else:
                    if 'max_pages' in self.config['ProjectInfo']:
                        del self.config['ProjectInfo']['max_pages']
                self.config['ProjectInfo']['max_retries'] = str(updated_data['max_retries'])
                if 'API' not in self.config:
                    self.config['API'] = {}
                self.config['API']['gemini_api_key'] = updated_data['api_key']
                if 'api_key_name' in updated_data and updated_data['api_key_name']:
                    self.config['API']['api_key_name'] = updated_data['api_key_name']
                if 'Startpromt' not in self.config:
                    self.config['Startpromt'] = {}
                self.config['Startpromt']['startpromt'] = updated_data['Startpromt']
                if 'MCP' not in self.config:
                    self.config['MCP'] = {}
                if updated_data.get('mcp_endpoint_id'):
                    self.config['MCP']['endpoint_id'] = updated_data['mcp_endpoint_id']
                elif 'endpoint_id' in self.config['MCP']:
                    del self.config['MCP']['endpoint_id']
                if 'Features' not in self.config:
                    self.config['Features'] = {}
                self.config['Features']['cache_enabled'] = str(updated_data.get('cache_enabled', True))
                self.config['Features']['terminology_enabled'] = str(updated_data.get('terminology_enabled', True))
                self.config['Features']['async_enabled'] = str(updated_data.get('async_enabled', False))
                self.config['Features']['async_threads'] = str(updated_data.get('async_threads', 3))
                if 'Batch' not in self.config:
                    self.config['Batch'] = {}
                self.config['Batch']['batch_enabled'] = str(updated_data.get('batch_enabled', False))
                self.config['Batch']['max_batch_chars'] = str(updated_data.get('max_batch_chars', 33000))
                self.config['Batch']['max_chapters_per_batch'] = str(updated_data.get('max_chapters_per_batch', 5))
                with open(config_path, 'w', encoding='utf-8') as configfile:
                    self.config.write(configfile)
                QMessageBox.information(self, tr("main_window.msg_settings_saved_title", "Ayarlar Kaydedildi"), tr("main_window.msg_settings_saved_body", "'{}' projesinin ayarları başarıyla kaydedildi.").format(project_name))
                self.update_file_list_from_selection()
            except Exception as e:
                QMessageBox.critical(self, tr("main_window.msg_settings_save_error_title", "Kaydetme Hatası"), tr("main_window.msg_settings_save_error_body", "Ayarlar kaydedilirken bir hata oluştu:\n{}").format(e))

    # Dosya Listesi Güncelle
    def sync_database_if_exists(self):
        """Toplu dosya işlemleri (Çeviri, İndirme, Bölme) bitiminde veritabanını diske göre günceller."""
        if not hasattr(self, 'current_project_path') or not self.current_project_path:
            return
        
        try:
            from core.database_manager import DatabaseManager
            db_mgr = DatabaseManager(self.current_project_path)
            if db_mgr.db_exists():
                from core.file_list_manager import FileListManager
                legacy_flm = FileListManager(self.current_project_path)
                db_mgr.sync_directory_to_db(legacy_flm)
        except Exception as e:
            from logger import app_logger
            app_logger.error(f"UI DB Sync Hatası: {e}")

    def refresh_ui_and_theme(self):
        """UI'yi ve aktif temayı yeniden yükler."""
        self.setWindowTitle(tr("main_window.title", "Novel Çeviri Aracı V2.4.0"))
        
        # Sol Panel başlık ve arama kutusu
        if hasattr(self, "projects_label"):
            self.projects_label.setText(tr("main_window.projects", "Projeler:"))
        if hasattr(self, "project_search_input"):
            self.project_search_input.setPlaceholderText(tr("main_window.search_project_placeholder", "🔍 Proje ara..."))
        if hasattr(self, "project_search_clear_btn"):
            self.project_search_clear_btn.setToolTip(tr("main_window.tooltip_clear_search", "Aramayı temizle"))
            
        # Orta Panel arama kutusu ve tablo başlıkları
        if hasattr(self, "file_search_input"):
            self.file_search_input.setPlaceholderText(tr("main_window.search_file_placeholder", "🔍 Dosya ara..."))
        if hasattr(self, "file_search_clear_btn"):
            self.file_search_clear_btn.setToolTip(tr("main_window.tooltip_clear_file_search", "Dosya aramasını temizle"))
            
        headers = [
            tr("main_window.table_header_check", "☑"),
            tr("main_window.table_header_original", "Orijinal"),
            tr("main_window.table_header_translated", "Çevrilen"),
            tr("main_window.table_header_date", "Tarih"),
            tr("main_window.table_header_size", "Boyut"),
            tr("main_window.table_header_status", "Durum"),
            tr("main_window.table_header_orig_token", "Orig.Token"),
            tr("main_window.table_header_trsl_token", "Trsl.Token")
        ]
        self.file_table.setHorizontalHeaderLabels(headers)

        self.update_file_list_from_selection()
        self.update_rigt_panel()
        self.update_status_bar()
        self.update_menu_bar()
        
        app_settings = load_app_settings()
        apply_theme(QApplication.instance(), app_settings.get("theme", "dark"))
        self.show_toast(tr("main_window.toast_ui_refreshed_title", "UI Yenilendi"), tr("main_window.toast_ui_refreshed_body", "Dosya listesi ve tema başarıyla yeniden yüklendi."))

    def update_rigt_panel(self):
        if hasattr(self, "downloadMethodLabel"):
            self.downloadMethodLabel.setText(tr("right_panel.download_method", "İndirme Yöntemi:"))
        if hasattr(self, "downloadMethodCombo"):
            self.downloadMethodCombo.setItemText(0, tr("right_panel.download_method_booktoki", "Booktoki JS İle İndir (Selenium)"))
            self.downloadMethodCombo.setItemText(1, tr("right_panel.download_method_69shuba", "69shuba JS İle İndir (Selenium)"))
            self.downloadMethodCombo.setItemText(2, tr("right_panel.download_method_novelfire", "Novelfire JS İle İndir (Selenium)"))
            self.downloadMethodCombo.setItemText(3, tr("right_panel.download_method_requests", "Normal Web Kazıma (Requests) (Tavsiye Edilmez)"))
        if hasattr(self, "startButton"):
            self.startButton.setText(tr("right_panel.btn_start_download", "⬇  İndirmeyi Başlat"))
        if hasattr(self, "workflowButton"):
            self.workflowButton.setText(tr("right_panel.btn_workflow", "🚀  Tam Otomatik İşlem"))
        if hasattr(self, "splitButton"):
            self.splitButton.setText(tr("right_panel.btn_split", "✂  Toplu Bölüm Ekle"))
        if hasattr(self, "translateButton"):
            self.translateButton.setText(tr("right_panel.btn_translate", "🌐  Seçilenleri Çevir"))
        if hasattr(self, "limit_checkbox"):
            self.limit_checkbox.setText(tr("right_panel.limit_translate", "Sayılı çevir"))
            self.limit_checkbox.setToolTip(tr("right_panel.limit_translate_tooltip", "İşaretlenirse sadece yandaki sayı kadar dosya çevrilip durur."))
        if hasattr(self, "shutdown_checkbox"):
            self.shutdown_checkbox.setText(tr("right_panel.shutdown_on_complete", "⚡ Çeviri Bitince Kapat"))
            self.shutdown_checkbox.setToolTip(tr("right_panel.shutdown_on_complete_tooltip", "Çeviri tamamlanınca bilgisayarı ONAYSIZ kapar"))
        if hasattr(self, "mergeButton"):
            self.mergeButton.setText(tr("right_panel.btn_merge", "🔗  Seçili Çevirileri Birleştir"))
        if hasattr(self, "stopTranslationButton"):
            self.stopTranslationButton.setText(tr("right_panel.btn_stop", "■  Çeviriyi Durdur"))
        if hasattr(self, "errorCheckButton"):
            self.errorCheckButton.setText(tr("right_panel.btn_error_check", "🔍  Çeviri Hata Kontrol"))
        if hasattr(self, "epubButton"):
            self.epubButton.setText(tr("right_panel.btn_epub", "📚  Seçilenleri EPUB Yap"))
        if hasattr(self, "token_count_button"):
            self.token_count_button.setText(tr("right_panel.btn_token_count", "🔢  Token Say"))
        if hasattr(self, "statusLabel"):
            self.statusLabel.setText(tr("right_panel.status_prefix", "Durum: {}").format(self._current_status))
        if hasattr(self, "total_tokens_label"):
            token_val = self.project_token_cache.get('total_combined_tokens', 0) if hasattr(self, 'project_token_cache') and self.project_token_cache else 0
            if self.project_list.currentItem():
                self.total_tokens_label.setText(tr("main_window.label_total_tokens", "Toplam Token (Orijinal + Çevrilen): {}").format(token_val))
            else:
                self.total_tokens_label.setText(tr("right_panel.label_total_tokens_short", "Toplam Token: {}").format(token_val))
        if hasattr(self, "total_original_tokens_label"):
            orig_val = self.project_token_cache.get('total_original_tokens', 0) if hasattr(self, 'project_token_cache') and self.project_token_cache else 0
            if self.project_list.currentItem():
                self.total_original_tokens_label.setText(tr("main_window.label_total_original_tokens", "Toplam Orijinal Token: {}").format(orig_val))
            else:
                self.total_original_tokens_label.setText(tr("right_panel.label_original_tokens_short", "Orijinal Token: {}").format(orig_val))
        if hasattr(self, "total_translated_tokens_label"):
            trsl_val = self.project_token_cache.get('total_translated_tokens', 0) if hasattr(self, 'project_token_cache') and self.project_token_cache else 0
            if self.project_list.currentItem():
                self.total_translated_tokens_label.setText(tr("main_window.label_total_translated_tokens", "Toplam Çevrilen Token: {}").format(trsl_val))
            else:
                self.total_translated_tokens_label.setText(tr("right_panel.label_translated_tokens_short", "Çevrilen Token: {}").format(trsl_val))
        if hasattr(self, "selectHighlightedButton"):
            self.selectHighlightedButton.setText(tr("right_panel.btn_select_highlighted", "☑  Seç (Vurgulananları İşaretle)"))
        if hasattr(self, "generateTerminologyButton"):
            self.generateTerminologyButton.setText(tr("right_panel.btn_ai_terminology", "🤖  YZ İle Terminoloji Üret"))
        if hasattr(self, "projectSettingsButton"):
            self.projectSettingsButton.setText(tr("right_panel.btn_project_settings", "⚙  Proje Ayarları"))
        if hasattr(self, "helpButton"):
            self.helpButton.setText(tr("right_panel.btn_help", "❓  Yardım"))

    def update_status_bar(self):
        if hasattr(self, "sb_refresh_btn"):
            self.sb_refresh_btn.setText(tr("status_bar.btn_refresh", "↻  UI Yenile"))
            self.sb_refresh_btn.setToolTip(tr("status_bar.btn_refresh_tooltip", "Dosya listesini yeniden yükle (UI Yenile)"))
        self.status_bar_mgr.update()

    def update_menu_bar(self):
        self.menuBar().clear()
        from ui.menu_bar_builder import build_menu_bar
        build_menu_bar(self)
    def update_file_list_from_selection(self):
        self.file_table.setRowCount(0)
        current_item = self.project_list.currentItem()
        if not current_item:
            self.current_project_path = None
            self.downloadMethodCombo.setEnabled(False)
            self.translateButton.setEnabled(False)
            self.splitButton.setEnabled(False)
            self.mergeButton.setEnabled(False)
            self.projectSettingsButton.setEnabled(False)
            self.selectHighlightedButton.setEnabled(False)
            if hasattr(self, 'token_count_button'):
                self.token_count_button.setEnabled(False)
            if hasattr(self, 'generateTerminologyButton'):
                self.generateTerminologyButton.setEnabled(False)
            if hasattr(self, 'total_tokens_label'):
                self.total_tokens_label.setText(tr("right_panel.label_total_tokens_short", "Toplam Token: {}").format(0))
                self.total_original_tokens_label.setText(tr("right_panel.label_original_tokens_short", "Orijinal Token: {}").format(0))
                self.total_translated_tokens_label.setText(tr("right_panel.label_translated_tokens_short", "Çevrilen Token: {}").format(0))
                self.total_tokens_label.setVisible(False)
                self.total_original_tokens_label.setVisible(False)
                self.total_translated_tokens_label.setVisible(False)
            if hasattr(self, 'token_progress_bar'):
                self.token_progress_bar.setVisible(False)
            return

        project_name = current_item.text()
        self.current_project_path = os.path.join(os.getcwd(), project_name)
        self.downloadMethodCombo.setEnabled(True)
        self.translateButton.setEnabled(True)
        self.splitButton.setEnabled(True)
        self.mergeButton.setEnabled(True)
        self.epubButton.setEnabled(True)
        self.projectSettingsButton.setEnabled(True)
        self.selectHighlightedButton.setEnabled(True)
        if hasattr(self, 'token_count_button'):
            self.token_count_button.setEnabled(True)
        if hasattr(self, 'errorCheckButton'):
            self.errorCheckButton.setEnabled(True)
        if hasattr(self, 'generateTerminologyButton'):
            self.generateTerminologyButton.setEnabled(True)

        from core.file_list_manager import FileListManager
        from ui.file_table_manager import FileTableManager
        manager = FileListManager(self.current_project_path)
        data = manager.get_file_list_data()
        self.project_token_cache = data['project_token_cache']
        table_manager = FileTableManager(self.file_table)
        table_manager.populate(data['sorted_entries'])

        if hasattr(self, 'total_original_tokens_label'):
            self.total_original_tokens_label.setText(tr("main_window.label_total_original_tokens", "Toplam Orijinal Token: {}").format(self.project_token_cache.get('total_original_tokens', 0)))
            self.total_translated_tokens_label.setText(tr("main_window.label_total_translated_tokens", "Toplam Çevrilen Token: {}").format(self.project_token_cache.get('total_translated_tokens', 0)))
            self.total_tokens_label.setText(tr("main_window.label_total_tokens", "Toplam Token (Orijinal + Çevrilen): {}").format(self.project_token_cache.get('total_combined_tokens', 0)))
            self.total_tokens_label.setVisible(True)
            self.total_original_tokens_label.setVisible(True)
            self.total_translated_tokens_label.setVisible(True)
        if hasattr(self, 'token_progress_bar'):
            self.token_progress_bar.setVisible(False)

    # UI Yardımcıları
    def _set_ui_state_on_process_start(self, button, text, bg_color, text_color, max_progress, status_text):
        self.startButton.setEnabled(False)
        self.splitButton.setEnabled(False)
        self.downloadMethodCombo.setEnabled(False)
        self.translateButton.setEnabled(False)
        self.mergeButton.setEnabled(False)
        self.projectSettingsButton.setEnabled(False)
        self.selectHighlightedButton.setEnabled(False)
        self.token_count_button.setEnabled(False)
        self.errorCheckButton.setEnabled(False)
        self.generateTerminologyButton.setEnabled(False)
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
        self.startButton.setEnabled(True)
        self.splitButton.setEnabled(True)
        self.downloadMethodCombo.setEnabled(True)
        self.translateButton.setEnabled(True)
        self.mergeButton.setEnabled(True)
        self.epubButton.setEnabled(True)
        self.projectSettingsButton.setEnabled(True)
        self.selectHighlightedButton.setEnabled(True)
        self.token_count_button.setEnabled(True)
        self.errorCheckButton.setEnabled(True)
        self.generateTerminologyButton.setEnabled(True)
        button.setEnabled(True)
        button.setText(text)
        button.setStyleSheet(f"background-color: {bg_color}; color: {text_color}; border-radius: 5px; padding: 10px;")
        self.progressBar.setVisible(False)
        self.statusLabel.setText(status_text)

    def _set_all_buttons_enabled_state(self, enabled):
        self.startButton.setEnabled(enabled)
        self.translateButton.setEnabled(enabled)
        self.mergeButton.setEnabled(enabled)
        self.errorCheckButton.setEnabled(enabled)
        self.projectSettingsButton.setEnabled(enabled)
        self.selectHighlightedButton.setEnabled(enabled)
        self.token_count_button.setEnabled(enabled)
        
    def add_file_to_table(self, file_path, file_name):
        pass    
    # Yardımcı Metotlar

    def on_shutdown_checkbox_toggled(self, checked):
        if checked:
            reply = QMessageBox.warning(self, tr("main_window.msg_shutdown_confirm_title", "Otomatik Kapatma"),
                                        tr("main_window.msg_shutdown_confirm_body", "İşlem bitince bilgisayar ONAYSIZ kapatılacak.\nDevam?"),
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                        QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                self.shutdown_checkbox.blockSignals(True)
                self.shutdown_checkbox.setChecked(False)
                self.shutdown_checkbox.blockSignals(False)

    def show_help_clicked(self):
        url = "https://github.com/utkucanc/yznvltranslate"
        QDesktopServices.openUrl(QUrl(url))

    def show_about_dialog(self):
        QMessageBox.about(self, tr("main_window.about_title", "Hakkında"),
                          tr("main_window.about_text",
                          "Novel Çeviri Aracı.\n\n"
                          "Bu uygulama UtkuCanC tarafından webnovel çevirilerini yapay zeka desteği ile çevirisininin yapılması amacıyla geliştirilmiştir.\n\n"
                          "Sürüm: 1.9.9 (Uygulama genelinde loglama sistemi eklendi. Token sayımı donma ve veri kaybolma hataları giderildi.)\n\n"
                          "Sürüm: 2.0.0 (MCP-API Desteği, JS Selenium İndirme, Cache Desteği, Terminoloji Desteği ve daha fazlası)\n\n"
                          "Sürüm: 2.1.0 (SRP yeniden yapılandırma, Batch Sistemi(Geliştirilmekte), Asenkron Sistemi, Proje Bazlı SQLite, Sistem iyileştirmesi)\n\n"
                          "Sürüm: 2.2.0 (Toplu Çeviri (Batch Mode) ile Asenkron Çeviri aynı anda kullanılabilir hale getirildi (Daha hızlı çeviri imkanı.). API Pool ve MCP Endpoint rotasyonu eklendi. Bazı sorunlar giderildi.)\n\n"
                          "Sürüm: 2.3.0 (Yeni bir arayüz ve iyileştirmelerle birlikte daha stabil ve hızlı bir deneyim sunuldu. Tema düzenleme paneli eklendi.)\n\n"
                          "Sürüm: 2.4.0 (Çoklu Dil ve Lokalizasyon Desteği)\n\n"
                          "Geliştirici: UtkuCanC\n"
                          "Mart 2026\n"))

    
    # Toast Bildirimi — Saf Qt Widget (System Tray showMessage KULLANILMAZ)
    # Nedeni: QSystemTrayIcon.showMessage() Windows native bildirimi oluşturur.
    # Tıklandığında Windows, bildirimi python.exe ile ilişkilendirir ve yeni
    # bir konsol penceresi açar. Bu davranış Qt sinyalleriyle engellenemez.

    def _setup_tray_icon(self):
        """Tray ikonu kurar (sadece simge için — showMessage kullanmıyoruz)."""
        try:
            from PyQt6.QtWidgets import QSystemTrayIcon
            if QSystemTrayIcon.isSystemTrayAvailable():
                self._tray_icon = QSystemTrayIcon(self)
                icon = QIcon("logo256.ico") if os.path.exists("logo256.ico") else QIcon()
                self._tray_icon.setIcon(icon)
                self._tray_icon.activated.connect(self._on_tray_activated)
                self._tray_icon.show()
        except Exception as e:
            app_logger.warning(f"Tray ikon kurulamadı: {e}")

    def _on_tray_activated(self, reason):
        from PyQt6.QtWidgets import QSystemTrayIcon
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.showNormal()
            self.activateWindow()
            self.raise_()

    def show_toast(self, title: str, message: str):
        """Ekranın sağ altında kayan Qt toast bildirimi gösterir."""
        try:
            settings = load_app_settings()
            if not settings.get("notifications_enabled", True):
                return
            toast = _ToastWidget(title, message, parent=None)
            toast.show_toast()
            app_logger.info(f"Toast bildirimi gösterildi: {title} — {message}")
        except Exception as e:
            app_logger.debug(f"Toast gösterilemedi: {e}")

    def _notify_translation_complete(self, total_files: int):
        self.show_toast(tr("main_window.toast_translation_complete_title", "✅ Çeviri Tamamlandı"), tr("main_window.toast_translation_complete_body", "{} dosya başarıyla çevrildi.").format(total_files))

    # ─────────────── Kapatma ───────────────
    def closeEvent(self, event):
        controllers = [
            self.download_ctrl, self.translation_ctrl, self.cleaning_ctrl,
            self.merge_ctrl, self.token_ctrl, self.chapter_check_ctrl,
            self.epub_ctrl, self.error_check_ctrl, self.split_ctrl
        ]
        running = [c for c in controllers if c.is_running()]
        if running:
            reply = QMessageBox.question(self, tr("main_window.shutdown_warning_title", "Uygulamayı Kapat"),
                                         tr("main_window.shutdown_warning_body", "Devam eden işlemler var. Çıkmak istediğinizden emin misiniz? Tüm işlemler durdurulacaktır."),
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                for c in running:
                    c.stop()
                for _ in range(5):
                    if not any(c.is_running() for c in controllers):
                        break
                    time.sleep(1)
                else:
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
