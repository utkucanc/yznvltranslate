import sys
import os
import configparser
from PyQt6.QtWidgets import (
    QDialog, QLineEdit, QFormLayout, QDialogButtonBox, 
    QMessageBox, QLabel, QApplication, QTextEdit, QListWidget, 
    QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QInputDialog,
    QSpinBox, QCheckBox, QGroupBox, QSplitter, QWidget, QProgressBar
)
from PyQt6.QtGui import QIntValidator, QFont, QIcon, QAction
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject, QSize
from logger import app_logger

# ─── V2.1.0 Geriye Uyumluluk Re-export'lar ───
# ui/ paketine taşınan sınıflar burada da erişilebilir kalır.
# Eski "from dialogs import X" çağrıları kırılmaz.

from ui.app_settings_dialog import AppSettingsDialog
from ui.file_preview_dialog import FilePreviewDialog
from ui.terminology_dialog import TerminologyDialog
from ui.prompt_editor_dialog import PromptEditorDialog
from ui.api_key_editor_dialog import ApiKeyEditorDialog




# --- Yardımcı Fonksiyonlar ---
def get_config_path(subfolder):
    """AppConfigs altındaki klasör yollarını döndürür."""
    base_path = os.getcwd()
    path = os.path.join(base_path, "AppConfigs", subfolder)
    if not os.path.exists(path):
        os.makedirs(path)
    return path

def load_files_to_combo(combobox, subfolder):
    """Belirtilen klasördeki txt dosyalarını combobox'a yükler."""
    folder = get_config_path(subfolder)
    combobox.clear()
    combobox.addItem("Seçiniz...", None)
    if os.path.exists(folder):
        files = sorted([f for f in os.listdir(folder) if f.endswith('.txt')])
        for f in files:
            file_path = os.path.join(folder, f)
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read().strip()
                # Item text: Dosya Adı, Item Data: Dosya İçeriği
                combobox.addItem(f.replace('.txt', ''), content)
            except:
                pass


class ProjectSettingsDialog(QDialog):
    """Mevcut proje ayarlarını düzenleme penceresi."""
    def __init__(self, project_name, project_link, max_pages, api_key, start_promt, gemini_version, parent=None,
                 mcp_endpoint_id=None, cache_enabled=True, terminology_enabled=True,
                 async_enabled=False, async_threads=3,
                 batch_enabled=False, max_batch_chars=33000, max_chapters_per_batch=5):
        super().__init__(parent)
        self.setWindowTitle(f"'{project_name}' Ayarları")
        self.setMinimumWidth(550)
        self.project_name = project_name
        layout = QFormLayout(self)

        self.projectNameLabel = QLabel(project_name)
        self.projectNameLabel.setStyleSheet("font-weight: bold;") 

        self.projectLinkInput = QLineEdit()
        self.projectLinkInput.setText(project_link)
        
        self.maxPagesInput = QLineEdit()
        if max_pages is not None:
            self.maxPagesInput.setText(str(max_pages))
            
        self.maxRetriesInput = QSpinBox()
        self.maxRetriesInput.setMinimum(1)
        self.maxRetriesInput.setMaximum(20)
        self.maxRetriesInput.setValue(parent.max_retries if hasattr(parent, 'max_retries') else 3)
        self.maxRetriesInput.setToolTip("Bir API hatası alındığında (Örn. 500) tekrar deneme sayısı.")
        
        # --- MCP Endpoint Seçimi (YENİ) ---
        mcp_group = QGroupBox("Yapay Zeka Kaynağı (MCP)")
        mcp_layout = QVBoxLayout()
        
        self.use_custom_endpoint = QCheckBox("Bu proje için özel bağlantı kullan")
        mcp_layout.addWidget(self.use_custom_endpoint)
        
        ep_layout = QHBoxLayout()
        self.endpoint_combo = QComboBox()
        self.endpoint_combo.setEnabled(False)
        self._load_endpoints(mcp_endpoint_id)
        
        self.mcp_manage_btn = QPushButton("MCP Yönet")
        self.mcp_manage_btn.setFixedWidth(100)
        self.mcp_manage_btn.clicked.connect(self.open_mcp_dialog)
        
        ep_layout.addWidget(self.endpoint_combo, 1)
        ep_layout.addWidget(self.mcp_manage_btn)
        mcp_layout.addLayout(ep_layout)
        mcp_group.setLayout(mcp_layout)
        
        self.use_custom_endpoint.toggled.connect(self.endpoint_combo.setEnabled)
        if mcp_endpoint_id:
            self.use_custom_endpoint.setChecked(True)
        
        # --- API Key Seçimi ---
        key_layout = QHBoxLayout()
        self.api_key_combo = QComboBox()
        self.api_key_combo.currentIndexChanged.connect(self.on_api_combo_changed)
        
        self.api_key_input = QLineEdit()
        self.api_key_input.setText(api_key)
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.edit_keys_btn = QPushButton("Düzenle")
        self.edit_keys_btn.clicked.connect(self.open_key_editor)
        
        key_layout.addWidget(self.api_key_combo, 1)
        key_layout.addWidget(self.edit_keys_btn)
        # --- Gemini  Versiyon Gösterimi ---
        gemini_layout = QHBoxLayout()
        self.gemini_version_label = QLabel(f"Mevcut Versiyon:")
        self.gemini_version_combo = QComboBox()
        self.gemini_version_combo.setEditable(True)
        self.gemini_version_combo.addItem(gemini_version)
        self.gemini_version_combo.setCurrentText(gemini_version)
        
        # --- Promt Seçimi ---
        promt_layout = QHBoxLayout()
        self.promt_combo = QComboBox()
        self.promt_combo.currentIndexChanged.connect(self.on_promt_combo_changed)
        
        self.edit_promt_btn = QPushButton("Düzenle")
        self.edit_promt_btn.clicked.connect(self.open_promt_editor)
        
        promt_layout.addWidget(self.promt_combo, 1)
        promt_layout.addWidget(self.edit_promt_btn)

        self.startpromtinput = QTextEdit()
        self.startpromtinput.setText(start_promt)

        # --- Prompt Generator Butonu (YENİ) ---
        self.prompt_gen_btn = QPushButton("⚡ Prompt Oluşturucu (Generator)")
        self.prompt_gen_btn.setStyleSheet("background-color: #E91E63; color: white; font-weight: bold; padding: 8px; border-radius: 4px;")
        self.prompt_gen_btn.clicked.connect(self.open_prompt_generator)

        # --- Otomatik Özellikler (Cache & Terminology) ---
        features_group = QGroupBox("Otomatik Özellikler")
        features_layout = QVBoxLayout()
        self.cache_checkbox = QCheckBox("Çeviri Önbelleği (Translation Cache)")
        self.cache_checkbox.setChecked(cache_enabled)
        self.cache_checkbox.setToolTip("Aynı metin tekrar çevrildiğinde API çağrısı yapmadan önbellekten döner.")
        self.terminology_checkbox = QCheckBox("Terminoloji Hafızası (Terminology Memory)")
        self.terminology_checkbox.setChecked(terminology_enabled)
        self.terminology_checkbox.setToolTip("Proje terminoloji sözlüğünü otomatik olarak prompta ekler.")
        features_layout.addWidget(self.cache_checkbox)
        features_layout.addWidget(self.terminology_checkbox)
        features_group.setLayout(features_layout)

        # --- Gelişmiş Özellikler (Asenkron Çeviri & DB Migration) ---
        advanced_group = QGroupBox("Performans ve Altyapı")
        advanced_layout = QFormLayout()
        
        self.async_checkbox = QCheckBox("Asenkron Çeviri Kullan (Eşzamanlı Çoklu Dosya)[Test Aşamasında-On Development]")
        self.async_checkbox.setChecked(async_enabled)
        self.async_checkbox.setToolTip("Çevirileri aynı anda başlatarak performansı ciddi oranda arttırır.")
        
        self.async_threads_spinbox = QSpinBox()
        self.async_threads_spinbox.setMinimum(1)
        self.async_threads_spinbox.setMaximum(100)
        self.async_threads_spinbox.setSingleStep(1)
        self.async_threads_spinbox.setValue(async_threads)
        self.async_threads_spinbox.setEnabled(async_enabled)
        self.async_checkbox.toggled.connect(self.async_threads_spinbox.setEnabled)

        # --- Toplu Çeviri (Batch Mode) ---
        self.batch_checkbox = QCheckBox("Þ Toplu Çeviri / Batch Mode [Test Aşamasında - On Development]")
        self.batch_checkbox.setChecked(batch_enabled)
        self.batch_checkbox.setToolTip(
            "Birden fazla bölümü tek API isteğine gruplayarak RPD kotasından daha fazla bölüm çevirir."
        )
        self.batch_checkbox.toggled.connect(self._on_batch_toggled)

        self.batch_chars_spinbox = QSpinBox()
        self.batch_chars_spinbox.setMinimum(5000)
        self.batch_chars_spinbox.setMaximum(1000000)
        self.batch_chars_spinbox.setSingleStep(1000)
        self.batch_chars_spinbox.setValue(max_batch_chars)
        self.batch_chars_spinbox.setEnabled(batch_enabled)
        self.batch_chars_spinbox.setToolTip("Bir batch'te gönderilebilecek maksimum karakter sayısı.")

        self.batch_chapters_spinbox = QSpinBox()
        self.batch_chapters_spinbox.setMinimum(1)
        self.batch_chapters_spinbox.setMaximum(100)
        self.batch_chapters_spinbox.setSingleStep(1)
        self.batch_chapters_spinbox.setValue(max_chapters_per_batch)
        self.batch_chapters_spinbox.setEnabled(batch_enabled)
        self.batch_chapters_spinbox.setToolTip("Bir batch'e konabilecek maksimum bölüm sayısı.")

        advanced_layout.addRow(self.async_checkbox)
        advanced_layout.addRow("İşlem Limiti (Thread):", self.async_threads_spinbox)
        advanced_layout.addRow(self.batch_checkbox)
        advanced_layout.addRow("Maks karakter/batch:", self.batch_chars_spinbox)
        advanced_layout.addRow("Maks bölüm/batch:", self.batch_chapters_spinbox)
        
        # --- Veritabanı Taşıma (Migration) ---
        from core.database_manager import DatabaseManager
        self.db_mgr = DatabaseManager(os.path.join(os.getcwd(), self.project_name))
        self.db_migrate_btn = QPushButton("Eski Projeyi Veritabanına Taşı (Hızlandır)")
        self.db_migrate_btn.setStyleSheet("background-color: #2196F3; color: white;")
        self.db_migrate_btn.clicked.connect(self.run_db_migration)
        
        if self.db_mgr.db_exists():
            self.db_migrate_btn.setVisible(False)
            
        advanced_layout.addRow(self.db_migrate_btn)
        advanced_group.setLayout(advanced_layout)

        # --- Terminoloji Sözlüğü (Yönetimi) Butonu ---
        self.terminology_manage_btn = QPushButton("Terminoloji Sözlüğünü Yönet/Düzenle")
        self.terminology_manage_btn.setStyleSheet("background-color: #9C27B0; color: white; font-weight: bold; padding: 8px; border-radius: 4px;")
        self.terminology_manage_btn.clicked.connect(self.open_terminology_dialog)
        
        layout.addRow("Proje Adı:", self.projectNameLabel)
        layout.addRow("Proje Linki:", self.projectLinkInput)
        layout.addRow("Maksimum Sayfa:", self.maxPagesInput)
        layout.addRow("Maksimum Deneme:", self.maxRetriesInput)
        layout.addRow(mcp_group)
        layout.addRow("API Key Seç:", key_layout)
        layout.addRow("Mevcut API Key:", self.api_key_input)
        layout.addRow("Promt Seç:", promt_layout)
        layout.addRow("Promt İçeriği:", self.startpromtinput)
        layout.addRow(self.prompt_gen_btn)
        layout.addRow(self.terminology_manage_btn)
        layout.addRow(features_group)
        layout.addRow(advanced_group)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        
        self.refresh_combos()

    def _on_batch_toggled(self, checked: bool):
        """Batch modu açılırken uyarı gösterir."""
        if checked:
            ret = QMessageBox.warning(
                self, "⚠️ Test Aşamasında&nbsp;— Toplu Çeviri",
                "<b>Toplu Çeviri (Batch Mode)</b> geliştirilmekte olan bir özelliktir.<br><br>"
                "• Hatalı veya eksik çeviri üretebilir.<br>"
                "• Parse başarısız olursa bölümler tekli moda düşer.<br><br>"
                "Devam etmek istiyor musunuz?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if ret != QMessageBox.StandardButton.Yes:
                # Kullanıcı reddetti — checkbox'u geri al
                self.batch_checkbox.blockSignals(True)
                self.batch_checkbox.setChecked(False)
                self.batch_checkbox.blockSignals(False)
                checked = False
        self.batch_chars_spinbox.setEnabled(checked)
        self.batch_chapters_spinbox.setEnabled(checked)

    def _load_endpoints(self, selected_id=None):
        """MCP endpoint listesini combo'ya yükler."""
        self.endpoint_combo.clear()
        self.endpoint_combo.addItem("Global Aktif Endpoint", None)
        try:
            from core.llm_provider import load_endpoints
            data = load_endpoints()
            for ep in data.get("endpoints", []):
                self.endpoint_combo.addItem(f"{ep['name']} ({ep['type']})", ep['id'])
                if selected_id and ep['id'] == selected_id:
                    self.endpoint_combo.setCurrentIndex(self.endpoint_combo.count() - 1)
        except Exception:
            pass

    def open_mcp_dialog(self):
        dlg = MCPServerDialog(self)
        dlg.exec()
        current_id = self.endpoint_combo.currentData()
        self._load_endpoints(current_id)

    def open_prompt_generator(self):
        """Prompt Generator dialog'unu açar."""
        try:
            from core.workers.prompt_generator import PromptGeneratorDialog
            dlg = PromptGeneratorDialog(self.project_name, self)
            if dlg.exec():
                generated = dlg.get_selected_prompt()
                if generated:
                    self.startpromtinput.setText(generated)
        except ImportError:
            QMessageBox.warning(self, "Uyarı", "Prompt Generator modülü henüz yüklenmemiş.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Prompt Generator açılamadı: {e}")

    def open_terminology_dialog(self):
        try:
            dlg = TerminologyDialog(os.path.join(os.getcwd(), self.project_name), self)
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Terminoloji penceresi açılamadı: {e}")

    def refresh_combos(self):
        load_files_to_combo(self.api_key_combo, "APIKeys")
        load_files_to_combo(self.promt_combo, "Promts")

    def on_api_combo_changed(self):
        data = self.api_key_combo.currentData()
        if data:
            self.api_key_input.setText(data)

    def on_promt_combo_changed(self):
        data = self.promt_combo.currentData()
        if data:
            self.startpromtinput.setText(data)

    def open_key_editor(self):
        dlg = ApiKeyEditorDialog(self)
        dlg.exec()
        self.refresh_combos()

    def open_promt_editor(self):
        dlg = PromptEditorDialog(self)
        dlg.exec()
        self.refresh_combos()

    def get_data(self):
        max_pages_text = self.maxPagesInput.text()
        max_pages = int(max_pages_text) if max_pages_text.isdigit() else None
        
        mcp_endpoint_id = None
        if self.use_custom_endpoint.isChecked():
            mcp_endpoint_id = self.endpoint_combo.currentData()
            
        api_key_name = self.api_key_combo.currentText()
        if api_key_name == "Seçiniz...":
            api_key_name = ""
        
        return {
            "link": self.projectLinkInput.text(),
            "max_pages": max_pages,
            "max_retries": self.maxRetriesInput.value(),
            "api_key": self.api_key_input.text(),
            "api_key_name": api_key_name,
            "Startpromt": self.startpromtinput.toPlainText(),
            "mcp_endpoint_id": mcp_endpoint_id,
            "cache_enabled": self.cache_checkbox.isChecked(),
            "terminology_enabled": self.terminology_checkbox.isChecked(),
            "async_enabled": self.async_checkbox.isChecked(),
            "async_threads": self.async_threads_spinbox.value(),
            "batch_enabled": self.batch_checkbox.isChecked(),
            "max_batch_chars": self.batch_chars_spinbox.value(),
            "max_chapters_per_batch": self.batch_chapters_spinbox.value(),
        }

    def run_db_migration(self):
        """Mevcut dizindekileri yavaş scan ile okuyup veritabanına geçirir."""
        from core.file_list_manager import FileListManager
        self.db_migrate_btn.setText("Taşınıyor... Lütfen bekleyin")
        self.db_migrate_btn.setEnabled(False)
        QApplication.processEvents()
        
        try:
            legacy_flm = FileListManager(os.path.join(os.getcwd(), self.project_name))
            success = self.db_mgr.sync_directory_to_db(legacy_flm)
            if success:
                QMessageBox.information(
                    self, "Başarılı", 
                    "Eski veriler başarıyla veritabanına taşındı!\nArtık dosya listeleri anında açılacak."
                )
                self.db_migrate_btn.setVisible(False)
            else:
                QMessageBox.warning(self, "Hata", "Veritabanına taşıma işlemi sırasında bir hata oluştu.")
                self.db_migrate_btn.setText("Eski Projeyi Veritabanına Taşı (Hızlandır)")
                self.db_migrate_btn.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Beklenmeyen bir hata oluştu:\n{e}")
            self.db_migrate_btn.setText("Eski Projeyi Veritabanına Taşı (Hızlandır)")
            self.db_migrate_btn.setEnabled(True)
