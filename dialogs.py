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

class GeminiVersionDialog(QDialog):
    """Gemini model versiyonunu seçmek veya manuel girmek için diyalog."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gemini Model Versiyonu")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("Kullanılacak Gemini Model Versiyonunu Seçin veya Girin:"))
        
        self.version_combo = QComboBox()
        self.version_combo.setEditable(True) # Manuel girişe izin ver
        
        # API'den modelleri çekmeyi dene
        models = []
        try:
            from google import genai
            keys_folder = get_config_path("APIKeys")
            if os.path.exists(keys_folder):
                api_keys = [f for f in os.listdir(keys_folder) if f.endswith('.txt')]
                if api_keys:
                    # İlk API anahtarını kullanarak modelleri çek
                    key_path = os.path.join(keys_folder, api_keys[0])
                    with open(key_path, 'r', encoding='utf-8') as f:
                        api_key = f.read().strip()
                    
                    if api_key:
                        client = genai.Client(api_key=api_key)
                        for m in client.models.list():
                            if 'generateContent' in m.supported_actions:
                                name = m.name.replace("models/", "")
                                models.append(name)
        except Exception as e:
            print(f"Model listesi çekilemedi: {e}")
            
        if not models:
            models = ["Manuel giriş yapınız..."]
            
        self.version_combo.addItems(models)
        
        # Mevcut ayarı yükle
        self.config_file = os.path.join(get_config_path(""), "GVersion.ini")
        self.config = configparser.ConfigParser()
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)
            current_version = self.config.get("Version", "model_name", fallback=models[0])
            self.version_combo.setCurrentText(current_version)
            
        layout.addWidget(self.version_combo)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel, self)
        buttons.accepted.connect(self.save_version)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def save_version(self):
        selected_version = self.version_combo.currentText().strip()
        if not selected_version:
             QMessageBox.warning(self, "Hata", "Versiyon boş olamaz.")
             return

        if not self.config.has_section("Version"):
            self.config.add_section("Version")
        
        self.config.set("Version", "model_name", selected_version)
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                self.config.write(f)
            QMessageBox.information(self, "Başarılı", "Versiyon kaydedildi.")
            self.accept()
        except Exception as e:
             QMessageBox.critical(self, "Hata", f"Kaydedilemedi: {e}")


class ApiKeyEditorDialog(QDialog):
    """API Anahtarlarını yönetmek için editör."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("API Key Editörü")
        self.resize(600, 400)
        self.keys_folder = get_config_path("APIKeys")
        
        main_layout = QHBoxLayout(self)
        
        # Sol Panel
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Kayıtlı Anahtarlar:"))
        self.key_list = QListWidget()
        self.key_list.currentItemChanged.connect(self.on_key_selected)
        left_layout.addWidget(self.key_list)
        
        btn_layout = QHBoxLayout()
        self.new_btn = QPushButton("Yeni")
        self.new_btn.clicked.connect(self.new_key)
        self.del_btn = QPushButton("Sil")
        self.del_btn.setStyleSheet("color: red;")
        self.del_btn.clicked.connect(self.delete_key)
        btn_layout.addWidget(self.new_btn)
        btn_layout.addWidget(self.del_btn)
        left_layout.addLayout(btn_layout)
        
        # Sağ Panel
        right_layout = QVBoxLayout()
        form = QFormLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Anahtar Adı (Örn: Ana Hesabım)")
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("AIzaSy...")
        form.addRow("Ad:", self.name_input)
        form.addRow("Key:", self.key_input)
        right_layout.addLayout(form)
        
        self.save_btn = QPushButton("Kaydet")
        self.save_btn.clicked.connect(self.save_key)
        right_layout.addWidget(self.save_btn)
        right_layout.addStretch()
        
        main_layout.addLayout(left_layout, 1)
        main_layout.addLayout(right_layout, 2)
        
        self.load_keys()
        
    def load_keys(self):
        self.key_list.clear()
        if os.path.exists(self.keys_folder):
            files = [f for f in os.listdir(self.keys_folder) if f.endswith('.txt')]
            for f in files:
                self.key_list.addItem(f.replace('.txt', ''))
        self.new_key()
        
    def on_key_selected(self, current, prev):
        if not current: return
        filename = current.text() + ".txt"
        path = os.path.join(self.keys_folder, filename)
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                self.name_input.setText(current.text())
                self.key_input.setText(f.read().strip())
                
    def new_key(self):
        self.key_list.clearSelection()
        self.name_input.clear()
        self.key_input.clear()
        
    def save_key(self):
        name = self.name_input.text().strip()
        key = self.key_input.text().strip()
        
        if not name or not key:
            QMessageBox.warning(self, "Eksik", "Ad ve Key alanları zorunludur.")
            return
            
        safe_name = "".join([c for c in name if c.isalnum() or c in (' ', '-', '_')]).strip()
        path = os.path.join(self.keys_folder, safe_name + ".txt")
        
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(key)
            self.load_keys()
            QMessageBox.information(self, "Başarılı", "API Anahtarı kaydedildi.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))
            
    def delete_key(self):
        current = self.key_list.currentItem()
        if not current: return
        
        if QMessageBox.question(self, "Sil", "Emin misiniz?") == QMessageBox.StandardButton.Yes:
            path = os.path.join(self.keys_folder, current.text() + ".txt")
            try:
                os.remove(path)
                self.load_keys()
            except: pass


class NewProjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Yeni Proje Oluştur")
        self.setMinimumWidth(500)
        layout = QFormLayout(self)
        
        self.projectNameInput = QLineEdit(self)
        self.projectLinkInput = QLineEdit(self)
        self.maxPagesInput = QLineEdit(self)
        self.maxPagesInput.setValidator(QIntValidator(1, 999999))
        
        self.maxRetriesInput = QSpinBox(self)
        self.maxRetriesInput.setMinimum(1)
        self.maxRetriesInput.setMaximum(20)
        self.maxRetriesInput.setValue(3)
        self.maxRetriesInput.setToolTip("Bir API hatası alındığında (Örn. 500) tekrar deneme sayısı.")
        
        # --- API Key Seçimi ---
        key_layout = QHBoxLayout()
        self.api_key_combo = QComboBox()
        self.api_key_combo.currentIndexChanged.connect(self.on_api_combo_changed)
        
        self.api_key_input = QLineEdit() # Manuel giriş veya combo sonucu buraya
        self.api_key_input.setPlaceholderText("Manuel giriş veya listeden seçin...")
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.edit_keys_btn = QPushButton("Düzenle")
        self.edit_keys_btn.setFixedWidth(60)
        self.edit_keys_btn.clicked.connect(self.open_key_editor)
        
        key_layout.addWidget(self.api_key_combo, 1)
        key_layout.addWidget(self.edit_keys_btn)
        
        # --- Promt Seçimi ---
        promt_layout = QHBoxLayout()
        self.promt_combo = QComboBox()
        self.promt_combo.currentIndexChanged.connect(self.on_promt_combo_changed)
        
        self.edit_promt_btn = QPushButton("Düzenle")
        self.edit_promt_btn.setFixedWidth(60)
        self.edit_promt_btn.clicked.connect(self.open_promt_editor)
        
        promt_layout.addWidget(self.promt_combo, 1)
        promt_layout.addWidget(self.edit_promt_btn)

        self.startpromtinput = QTextEdit(self)
        self.startpromtinput.setPlaceholderText("Seçilen veya manuel girilen promt buraya gelecek...")
        
        # --- MCP Endpoint Seçimi ---
        mcp_group = QGroupBox("Yapay Zeka Kaynağı (MCP)")
        mcp_layout = QVBoxLayout()
        
        self.use_custom_endpoint = QCheckBox("Bu proje için özel bağlantı kullan")
        mcp_layout.addWidget(self.use_custom_endpoint)
        
        ep_layout = QHBoxLayout()
        self.endpoint_combo = QComboBox()
        self.endpoint_combo.setEnabled(False)
        self._load_endpoints()
        
        self.mcp_manage_btn = QPushButton("MCP Yönet")
        self.mcp_manage_btn.setFixedWidth(100)
        self.mcp_manage_btn.clicked.connect(self.open_mcp_dialog)
        
        ep_layout.addWidget(self.endpoint_combo, 1)
        ep_layout.addWidget(self.mcp_manage_btn)
        mcp_layout.addLayout(ep_layout)
        mcp_group.setLayout(mcp_layout)
        
        self.use_custom_endpoint.toggled.connect(self.endpoint_combo.setEnabled)
        
        layout.addRow("Proje Adı:", self.projectNameInput)
        layout.addRow("Proje Linki:", self.projectLinkInput)
        layout.addRow("Maksimum Sayfa:", self.maxPagesInput)
        layout.addRow("Maksimum Deneme:", self.maxRetriesInput)
        layout.addRow(mcp_group)
        layout.addRow("API Key Seç:", key_layout)
        layout.addRow("Seçili API Key:", self.api_key_input)
        layout.addRow("Promt Seç:", promt_layout)
        layout.addRow("Promt İçeriği:", self.startpromtinput)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        
        self.refresh_combos()

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
        
    def _load_endpoints(self, selected_id=None):
        """MCP endpoint listesini combo'ya yükler."""
        self.endpoint_combo.clear()
        self.endpoint_combo.addItem("Global Aktif Endpoint", None)
        try:
            from llm_provider import load_endpoints
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
        
    def open_promt_editor(self):
        dlg = PromptEditorDialog(self)
        dlg.exec()
        self.refresh_combos()

    def get_data(self):
        max_pages_text = self.maxPagesInput.text()
        max_pages = int(max_pages_text) if max_pages_text.isdigit() else None
        
        api_key_name = self.api_key_combo.currentText()
        if api_key_name == "Seçiniz...":
            api_key_name = ""
            
        mcp_endpoint_id = None
        if self.use_custom_endpoint.isChecked():
            mcp_endpoint_id = self.endpoint_combo.currentData()
            
        return self.projectNameInput.text(), self.projectLinkInput.text(), max_pages, self.maxRetriesInput.value(), self.api_key_input.text(), self.startpromtinput.toPlainText(), api_key_name, mcp_endpoint_id


class ProjectSettingsDialog(QDialog):
    """Mevcut proje ayarlarını düzenlemek için."""
    def __init__(self, project_name, project_link, max_pages, api_key, start_promt, gemini_version, parent=None, mcp_endpoint_id=None, cache_enabled=True, terminology_enabled=True):
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
        layout.addRow(features_group)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        
        self.refresh_combos()

    def _load_endpoints(self, selected_id=None):
        """MCP endpoint listesini combo'ya yükler."""
        self.endpoint_combo.clear()
        self.endpoint_combo.addItem("Global Aktif Endpoint", None)
        try:
            from llm_provider import load_endpoints
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
            from prompt_generator import PromptGeneratorDialog
            dlg = PromptGeneratorDialog(self.project_name, self)
            if dlg.exec():
                generated = dlg.get_selected_prompt()
                if generated:
                    self.startpromtinput.setText(generated)
        except ImportError:
            QMessageBox.warning(self, "Uyarı", "Prompt Generator modülü henüz yüklenmemiş.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Prompt Generator açılamadı: {e}")

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
            "terminology_enabled": self.terminology_checkbox.isChecked()
        }

class PromptEditorDialog(QDialog):
    """Kayıtlı Promtları düzenlemek için."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Promt Editörü")
        self.resize(800, 600)
        self.prompts_folder = get_config_path("Promts")

        # Ana Düzen
        main_layout = QHBoxLayout(self)

        # --- Sol Panel (Liste) ---
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Kayıtlı Promtlar:"))
        
        self.prompt_list_widget = QListWidget()
        self.prompt_list_widget.currentItemChanged.connect(self.on_prompt_selected)
        left_layout.addWidget(self.prompt_list_widget)

        # Yeni ve Sil Butonları
        button_layout = QHBoxLayout()
        self.new_btn = QPushButton("Yeni")
        self.new_btn.clicked.connect(self.new_prompt)
        self.delete_btn = QPushButton("Sil")
        self.delete_btn.setStyleSheet("color: red;")
        self.delete_btn.clicked.connect(self.delete_prompt)
        button_layout.addWidget(self.new_btn)
        button_layout.addWidget(self.delete_btn)
        left_layout.addLayout(button_layout)

        # --- Sağ Panel (Editör) ---
        right_layout = QVBoxLayout()
        
        form_layout = QFormLayout()
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Promt Başlığı (Dosya Adı)")
        form_layout.addRow("Başlık:", self.title_input)
        right_layout.addLayout(form_layout)
        
        right_layout.addWidget(QLabel("Promt İçeriği:"))
        self.content_edit = QTextEdit()
        right_layout.addWidget(self.content_edit)

        # Kaydet Butonu
        self.save_btn = QPushButton("Kaydet")
        self.save_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 5px;")
        self.save_btn.clicked.connect(self.save_prompt)
        right_layout.addWidget(self.save_btn)

        # Panelleri birleştir
        main_layout.addLayout(left_layout, 1)
        main_layout.addLayout(right_layout, 2)

        self.load_prompts()

    def load_prompts(self):
        """Klasördeki .txt dosyalarını listeye yükler."""
        self.prompt_list_widget.clear()
        if os.path.exists(self.prompts_folder):
            files = [f for f in os.listdir(self.prompts_folder) if f.endswith('.txt')]
            for f in files:
                self.prompt_list_widget.addItem(f.replace('.txt', ''))
        
        self.title_input.clear()
        self.content_edit.clear()

    def on_prompt_selected(self, current, previous):
        if not current:
            return
        
        filename = current.text() + ".txt"
        filepath = os.path.join(self.prompts_folder, filename)
        
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.title_input.setText(current.text())
                self.content_edit.setText(content)
            except Exception as e:
                QMessageBox.warning(self, "Hata", f"Dosya okunamadı: {e}")

    def new_prompt(self):
        self.prompt_list_widget.clearSelection()
        self.title_input.clear()
        self.content_edit.clear()
        self.title_input.setFocus()

    def save_prompt(self):
        title = self.title_input.text().strip()
        content = self.content_edit.toPlainText()

        if not title:
            QMessageBox.warning(self, "Eksik", "Lütfen bir başlık giriniz.")
            return

        safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '-', '_')]).strip()
        if not safe_title:
             QMessageBox.warning(self, "Geçersiz", "Başlık geçersiz karakterler içeriyor.")
             return

        new_filename = safe_title + ".txt"
        new_filepath = os.path.join(self.prompts_folder, new_filename)

        try:
            with open(new_filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            QMessageBox.information(self, "Başarılı", "Promt kaydedildi.")
            self.load_prompts()
            items = self.prompt_list_widget.findItems(safe_title, Qt.MatchFlag.MatchExactly)
            if items:
                self.prompt_list_widget.setCurrentItem(items[0])
                
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Kaydetme başarısız: {e}")

    def delete_prompt(self):
        current_item = self.prompt_list_widget.currentItem()
        if not current_item:
            return

        title = current_item.text()
        filename = title + ".txt"
        filepath = os.path.join(self.prompts_folder, filename)

        reply = QMessageBox.question(self, "Sil", f"'{title}' promtunu silmek istediğinize emin misiniz?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
                    self.load_prompts()
                    self.new_prompt() 
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Silme başarısız: {e}")


# ─────────────────────── MCP Server Dialog ───────────────────────

class MCPServerDialog(QDialog):
    """MCP Sunucu Yönetim Paneli — Endpoint ekleme, düzenleme, silme ve anahtar yönetimi."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Yapay Zeka Kaynağı Yönetimi (MCP)")
        self.resize(900, 600)
        
        main_layout = QHBoxLayout(self)
        
        # ── Sol Panel: Endpoint Listesi ──
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Kayıtlı Sunucular:"))
        
        self.endpoint_list = QListWidget()
        self.endpoint_list.currentItemChanged.connect(self.on_endpoint_selected)
        left_layout.addWidget(self.endpoint_list)
        
        btn_layout = QHBoxLayout()
        self.new_btn = QPushButton("Yeni")
        self.new_btn.clicked.connect(self.new_endpoint)
        self.del_btn = QPushButton("Sil")
        self.del_btn.setStyleSheet("color: red;")
        self.del_btn.clicked.connect(self.delete_endpoint)
        btn_layout.addWidget(self.new_btn)
        btn_layout.addWidget(self.del_btn)
        left_layout.addLayout(btn_layout)
        
        # Aktif endpoint seçimi
        active_layout = QHBoxLayout()
        self.set_active_btn = QPushButton("Aktif Yap")
        self.set_active_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.set_active_btn.clicked.connect(self.set_active_endpoint)
        active_layout.addWidget(self.set_active_btn)
        left_layout.addLayout(active_layout)
        
        # ── Sağ Panel: Endpoint Formu ──
        right_layout = QVBoxLayout()
        
        form = QFormLayout()
        self.id_input = QLineEdit()
        self.id_input.setPlaceholderText("benzersiz_kimlik")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Sunucu Adı")
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["gemini", "openai_compatible"])
        
        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("model-id (ör: gemini-2.5-flash)")
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://api.example.com/v1 (boş = varsayılan)")
        
        self.rotation_check = QCheckBox("Anahtar Rotasyonu (Key Rotation)")
        self.rotation_check.setChecked(True)
        
        self.headers_input = QLineEdit()
        self.headers_input.setPlaceholderText('{"HTTP-Referer": "...", "X-Title": "..."}')
        
        form.addRow("ID:", self.id_input)
        form.addRow("Ad:", self.name_input)
        form.addRow("Tür:", self.type_combo)
        form.addRow("Model ID:", self.model_input)
        form.addRow("Base URL:", self.url_input)
        form.addRow(self.rotation_check)
        form.addRow("Headers (JSON):", self.headers_input)
        right_layout.addLayout(form)
        
        # API Anahtarları
        right_layout.addWidget(QLabel("API Anahtarları (her satıra bir tane):"))
        self.keys_edit = QTextEdit()
        self.keys_edit.setPlaceholderText("apikey_1\napikey_2\napikey_3")
        self.keys_edit.setMaximumHeight(120)
        right_layout.addWidget(self.keys_edit)
        
        # Butonlar
        action_layout = QHBoxLayout()
        self.save_btn = QPushButton("💾 Kaydet")
        self.save_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 6px;")
        self.save_btn.clicked.connect(self.save_endpoint)
        
        self.test_btn = QPushButton("🔗 Bağlantı Testi")
        self.test_btn.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold; padding: 6px;")
        self.test_btn.clicked.connect(self.test_connection)
        
        action_layout.addWidget(self.save_btn)
        action_layout.addWidget(self.test_btn)
        right_layout.addLayout(action_layout)
        
        self.test_result_label = QLabel("")
        self.test_result_label.setWordWrap(True)
        right_layout.addWidget(self.test_result_label)
        
        right_layout.addStretch()
        
        main_layout.addLayout(left_layout, 1)
        main_layout.addLayout(right_layout, 2)
        
        self._load_list()
    
    def _load_list(self):
        """Endpoint listesini yükler."""
        self.endpoint_list.clear()
        try:
            from llm_provider import load_endpoints
            data = load_endpoints()
            self._active_id = data.get("active_endpoint_id", "")
            for ep in data.get("endpoints", []):
                prefix = "✅ " if ep["id"] == self._active_id else "   "
                self.endpoint_list.addItem(f"{prefix}{ep['name']} [{ep['type']}]")
        except Exception as e:
            QMessageBox.warning(self, "Uyarı", f"Endpoint listesi yüklenemedi: {e}")
    
    def _get_endpoints_data(self) -> dict:
        try:
            from llm_provider import load_endpoints
            return load_endpoints()
        except Exception:
            return {"active_endpoint_id": "", "endpoints": []}
    
    def on_endpoint_selected(self, current, previous):
        if not current:
            return
        idx = self.endpoint_list.row(current)
        data = self._get_endpoints_data()
        endpoints = data.get("endpoints", [])
        if 0 <= idx < len(endpoints):
            ep = endpoints[idx]
            self.id_input.setText(ep.get("id", ""))
            self.name_input.setText(ep.get("name", ""))
            self.type_combo.setCurrentText(ep.get("type", "gemini"))
            self.model_input.setText(ep.get("model_id", ""))
            self.url_input.setText(ep.get("base_url", "") or "")
            self.rotation_check.setChecked(ep.get("use_key_rotation", True))
            import json
            self.headers_input.setText(json.dumps(ep.get("headers", {})) if ep.get("headers") else "")
            
            # Anahtarları yükle
            try:
                from llm_provider import load_api_keys
                keys = load_api_keys(ep["id"])
                self.keys_edit.setText("\n".join(keys))
            except Exception:
                self.keys_edit.clear()
    
    def new_endpoint(self):
        self.endpoint_list.clearSelection()
        self.id_input.clear()
        self.name_input.clear()
        self.type_combo.setCurrentIndex(0)
        self.model_input.clear()
        self.url_input.clear()
        self.rotation_check.setChecked(True)
        self.headers_input.clear()
        self.keys_edit.clear()
        self.test_result_label.clear()
    
    def save_endpoint(self):
        ep_id = self.id_input.text().strip()
        ep_name = self.name_input.text().strip()
        
        if not ep_id or not ep_name:
            QMessageBox.warning(self, "Eksik", "ID ve Ad alanları zorunludur.")
            return
        
        import json as _json
        headers = {}
        headers_text = self.headers_input.text().strip()
        if headers_text:
            try:
                headers = _json.loads(headers_text)
            except _json.JSONDecodeError:
                QMessageBox.warning(self, "Hata", "Headers alanı geçerli JSON formatında olmalıdır.")
                return
        
        new_ep = {
            "id": ep_id,
            "name": ep_name,
            "type": self.type_combo.currentText(),
            "model_id": self.model_input.text().strip(),
            "base_url": self.url_input.text().strip() or None,
            "use_key_rotation": self.rotation_check.isChecked(),
            "headers": headers
        }
        
        try:
            from llm_provider import load_endpoints, save_endpoints, save_api_keys
            data = load_endpoints()
            endpoints = data.get("endpoints", [])
            
            # Mevcut endpoint'i güncelle veya yeni ekle
            found = False
            for i, ep in enumerate(endpoints):
                if ep["id"] == ep_id:
                    endpoints[i] = new_ep
                    found = True
                    break
            if not found:
                endpoints.append(new_ep)
            
            data["endpoints"] = endpoints
            save_endpoints(data)
            
            # Anahtarları kaydet
            keys_text = self.keys_edit.toPlainText().strip()
            keys = [k.strip() for k in keys_text.split("\n") if k.strip()]
            save_api_keys(ep_id, keys)
            
            QMessageBox.information(self, "Başarılı", f"'{ep_name}' kaydedildi.")
            self._load_list()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Kaydetme hatası: {e}")
    
    def delete_endpoint(self):
        current = self.endpoint_list.currentItem()
        if not current:
            return
        idx = self.endpoint_list.row(current)
        
        if QMessageBox.question(self, "Sil", "Bu endpoint'i silmek istediğinize emin misiniz?") != QMessageBox.StandardButton.Yes:
            return
        
        try:
            from llm_provider import load_endpoints, save_endpoints
            data = load_endpoints()
            endpoints = data.get("endpoints", [])
            if 0 <= idx < len(endpoints):
                removed = endpoints.pop(idx)
                data["endpoints"] = endpoints
                # Aktif endpoint silindiyse sıfırla
                if data.get("active_endpoint_id") == removed.get("id"):
                    data["active_endpoint_id"] = endpoints[0]["id"] if endpoints else ""
                save_endpoints(data)
                self._load_list()
                self.new_endpoint()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Silme hatası: {e}")
    
    def set_active_endpoint(self):
        current = self.endpoint_list.currentItem()
        if not current:
            return
        idx = self.endpoint_list.row(current)
        
        try:
            from llm_provider import load_endpoints, save_endpoints
            data = load_endpoints()
            endpoints = data.get("endpoints", [])
            if 0 <= idx < len(endpoints):
                data["active_endpoint_id"] = endpoints[idx]["id"]
                save_endpoints(data)
                QMessageBox.information(self, "Başarılı", f"'{endpoints[idx]['name']}' aktif endpoint olarak ayarlandı.")
                self._load_list()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Aktif ayarlama hatası: {e}")
    
    def test_connection(self):
        self.test_result_label.setText("Bağlantı test ediliyor...")
        self.test_result_label.setStyleSheet("color: orange;")
        QApplication.processEvents()
        
        ep_id = self.id_input.text().strip()
        keys_text = self.keys_edit.toPlainText().strip()
        keys = [k.strip() for k in keys_text.split("\n") if k.strip()]
        
        if not keys:
            self.test_result_label.setText("❌ API anahtarı girilmemiş.")
            self.test_result_label.setStyleSheet("color: red;")
            return
        
        # Rastgele bir anahtar seç
        import random
        test_key = random.choice(keys)
        
        try:
            from llm_provider import LLMProvider
            import json as _json
            headers = {}
            if self.headers_input.text().strip():
                try:
                    headers = _json.loads(self.headers_input.text().strip())
                except:
                    pass
            
            ep_config = {
                "id": ep_id,
                "name": self.name_input.text().strip(),
                "type": self.type_combo.currentText(),
                "model_id": self.model_input.text().strip(),
                "base_url": self.url_input.text().strip() or None,
                "use_key_rotation": False,
                "headers": headers
            }
            
            provider = LLMProvider(endpoint=ep_config, api_key=test_key)
            success, message = provider.test_connection()
            
            if success:
                self.test_result_label.setText(f"✅ {message}")
                self.test_result_label.setStyleSheet("color: green;")
            else:
                self.test_result_label.setText(f"❌ {message}")
                self.test_result_label.setStyleSheet("color: red;")
        except Exception as e:
            self.test_result_label.setText(f"❌ Hata: {e}")
            self.test_result_label.setStyleSheet("color: red;")


# ─────────────────────── Terminology Dialog ───────────────────────

class TerminologyDialog(QDialog):
    """Proje bazlı terminoloji/terim sözlüğü yönetim paneli."""

    def __init__(self, project_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Terminoloji Sözlüğü")
        self.resize(650, 500)
        self.project_path = project_path

        from terminology.terminology_manager import TerminologyManager
        self.manager = TerminologyManager(project_path)

        layout = QVBoxLayout(self)

        # Tablo
        from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Kaynak Terim", "Hedef Terim", "Not"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        # Yeni terim ekleme
        add_group = QGroupBox("Yeni Terim Ekle")
        add_layout = QHBoxLayout()
        self.source_input = QLineEdit()
        self.source_input.setPlaceholderText("Kaynak (ör: 黑暗之王)")
        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText("Hedef (ör: Karanlık Kral)")
        self.note_input = QLineEdit()
        self.note_input.setPlaceholderText("Not (opsiyonel)")

        add_btn = QPushButton("➕ Ekle")
        add_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        add_btn.clicked.connect(self.add_term)

        add_layout.addWidget(self.source_input)
        add_layout.addWidget(self.target_input)
        add_layout.addWidget(self.note_input)
        add_layout.addWidget(add_btn)
        add_group.setLayout(add_layout)
        layout.addWidget(add_group)

        # Butonlar
        btn_layout = QHBoxLayout()

        del_btn = QPushButton("🗑️ Seçileni Sil")
        del_btn.setStyleSheet("color: red;")
        del_btn.clicked.connect(self.delete_term)

        import_btn = QPushButton("📥 İçe Aktar")
        import_btn.clicked.connect(self.import_terms)

        export_btn = QPushButton("📤 Dışa Aktar")
        export_btn.clicked.connect(self.export_terms)

        clear_btn = QPushButton("🧹 Tümünü Temizle")
        clear_btn.clicked.connect(self.clear_terms)

        btn_layout.addWidget(del_btn)
        btn_layout.addWidget(import_btn)
        btn_layout.addWidget(export_btn)
        btn_layout.addWidget(clear_btn)
        btn_layout.addStretch()

        close_btn = QPushButton("Kapat")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

        self._refresh_table()

    def _refresh_table(self):
        from PyQt6.QtWidgets import QTableWidgetItem
        terms = self.manager.get_all_terms()
        self.table.setRowCount(len(terms))
        for row, t in enumerate(terms):
            self.table.setItem(row, 0, QTableWidgetItem(t.get("source", "")))
            self.table.setItem(row, 1, QTableWidgetItem(t.get("target", "")))
            self.table.setItem(row, 2, QTableWidgetItem(t.get("note", "")))

    def add_term(self):
        source = self.source_input.text().strip()
        target = self.target_input.text().strip()
        note = self.note_input.text().strip()
        if not source or not target:
            QMessageBox.warning(self, "Eksik", "Kaynak ve hedef terim gereklidir.")
            return
        self.manager.add_term(source, target, note)
        self.source_input.clear()
        self.target_input.clear()
        self.note_input.clear()
        self._refresh_table()

    def delete_term(self):
        row = self.table.currentRow()
        if row < 0:
            return
        source = self.table.item(row, 0).text()
        self.manager.remove_term(source)
        self._refresh_table()

    def import_terms(self):
        text, ok = QInputDialog.getMultiLineText(
            self, "İçe Aktar",
            "Her satıra bir terim girin (kaynak=hedef formatında):",
            ""
        )
        if ok and text:
            count = self.manager.import_from_text(text)
            QMessageBox.information(self, "Başarılı", f"{count} terim içe aktarıldı.")
            self._refresh_table()

    def export_terms(self):
        text = self.manager.export_to_text()
        if not text:
            QMessageBox.information(self, "Boş", "Dışa aktarılacak terim yok.")
            return

        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, "Terimleri Kaydet", "terminology.txt", "Text Files (*.txt)")
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(text)
            QMessageBox.information(self, "Başarılı", f"Terimler kaydedildi: {path}")

    def clear_terms(self):
        reply = QMessageBox.question(
            self, "Tümünü Temizle",
            "Tüm terimleri silmek istediğinize emin misiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.manager.clear()
            self._refresh_table()

# ─────────────────────── Post-Download Actions Dialog ───────────────────────

class PostDownloadDialog(QDialog):
    """İndirme bittiğinde kullanıcıya sunulan aksiyonlar (Klasör Aç, Ayır, Kapat)."""
    def __init__(self, file_path, file_name, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.file_name = file_name
        self.setWindowTitle("İndirme Tamamlandı")
        self.setFixedWidth(450)
        
        layout = QVBoxLayout(self)
        
        # Bilgi Mesajı
        title_label = QLabel("✅ İndirme İşlemi Başarılı")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #4CAF50; margin-bottom: 5px;")
        layout.addWidget(title_label)
        
        info_label = QLabel(f"İndirilen dosya:\n{self.file_name}")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("margin-bottom: 20px; color: #E0E0E0;")
        layout.addWidget(info_label)
        
        # Butonlar
        btn_layout = QVBoxLayout()
        
        self.open_path_btn = QPushButton("📁 Dosya Yolunu Aç")
        self.open_path_btn.setStyleSheet("padding: 10px; background-color: #2196F3; color: white;")
        self.open_path_btn.clicked.connect(self.open_folder)
        btn_layout.addWidget(self.open_path_btn)
        
        self.split_btn = QPushButton("✂️ Bölümleri Ayır (Split)")
        self.split_btn.setStyleSheet("padding: 10px; background-color: #9C27B0; color: white;")
        self.split_btn.clicked.connect(self.start_splitting)
        btn_layout.addWidget(self.split_btn)
        
        self.close_btn = QPushButton("🚪 Kapat - Ana Ekrana Dön")
        self.close_btn.setStyleSheet("padding: 10px; margin-top: 10px;")
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)
        
        layout.addLayout(btn_layout)
        
        # İlerleme Çubuğu (Başlangıçta gizli)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("margin-top: 10px;")
        layout.addWidget(self.progress_bar)
        
        self.split_thread = None
        self.split_worker = None

    def open_folder(self):
        """Dosyanın bulunduğu klasörü açar."""
        folder = os.path.dirname(self.file_path)
        try:
            # Windows için klasörü aç
            os.startfile(folder)
            app_logger.info(f"PostDownloadDialog: Klasör açıldı -> {folder}")
        except Exception as e:
            # Diğer OS'ler veya hata durumu için alternatif
            import platform
            try:
                if platform.system() == "Windows":
                    os.startfile(folder)
                elif platform.system() == "Darwin":
                    import subprocess
                    subprocess.Popen(["open", folder])
                else:
                    import subprocess
                    subprocess.Popen(["xdg-open", folder])
            except:
                QMessageBox.warning(self, "Hata", f"Klasör açılamadı: {e}")

    def start_splitting(self):
        """SplitWorker başlatarak bölümleri ayırır."""
        from split_worker import SplitWorker # Import yerel
        
        # output_folder = os.path.join(os.path.dirname(self.file_path), os.path.splitext(self.file_name)[0] + "_bolumler")
        # print(output_folder)
        # print(self.file_path)
        # print(self.file_name)
        output_folder = os.path.dirname(self.file_path)
        self.split_btn.setEnabled(False)
        self.close_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.split_thread = QThread()
        self.split_worker = SplitWorker(self.file_path, output_folder)
        self.split_worker.moveToThread(self.split_thread)
        
        self.split_thread.started.connect(self.split_worker.run)
        self.split_worker.progress.connect(self.update_progress)
        self.split_worker.finished.connect(self.on_split_finished)
        self.split_worker.error.connect(self.on_split_error)
        
        self.split_thread.start()
        app_logger.info(f"PostDownloadDialog: Bölüm ayırma başlatıldı -> {output_folder}")

    def update_progress(self, current, total):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)

    def on_split_finished(self):
        self.split_thread.quit()
        self.split_thread.wait()
        os.remove(self.file_path)
        self.progress_bar.setVisible(False)
        QMessageBox.information(self, "Başarılı", "Bölümler başarıyla ayrıldı.")
        app_logger.info("PostDownloadDialog: Bölüm ayırma tamamlandı.")
        self.accept()

    def on_split_error(self, message):
        self.split_thread.quit()
        self.split_thread.wait()
        
        self.split_btn.setEnabled(True)
        self.close_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Hata", f"Ayırma hatası: {message}")
        app_logger.error(f"PostDownloadDialog: Ayırma hatası -> {message}")

# ─────────────────────── Selenium Control Dialog ───────────────────────

class SeleniumMenuDialog(QDialog):
    """Selenium ile indirme yaparken Cloudflare ve JS yönetimi için diyalog."""
    def __init__(self, worker, parent=None):
        super().__init__(parent)
        self.worker = worker
        self.setWindowTitle("Selenium Kontrol Paneli")
        self.setFixedWidth(400)
        # Pencereyi her zaman üstte tut özelliği kaldırıldı (istek üzerine)
        # self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        
        layout = QVBoxLayout(self)
        
        info_label = QLabel("Açılan tarayıcıda Cloudflare veya bot kontrolünü aşın. "
                            "Kitabın ilk bölüm sayfasına geldiğinizde butonları kullanın.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("margin-bottom: 10px; color: #E0E0E0;")
        layout.addWidget(info_label)
        
        self.opened_btn = QPushButton("1. İçerik 1. bölümü açıldı")
        self.opened_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 12px; font-weight: bold; border-radius: 5px;")
        self.opened_btn.clicked.connect(self.on_opened_clicked)
        layout.addWidget(self.opened_btn)
        
        self.shuba_btn = QPushButton("2. 69shubao için indirmeyi başlat")
        self.shuba_btn.setEnabled(False)
        # Başlangıçta pasif/gri stil
        self.shuba_btn.setStyleSheet("background-color: #9E9E9E; color: #E0E0E0; padding: 10px; border-radius: 5px;")
        self.shuba_btn.clicked.connect(lambda: self.start_download("shuba"))
        layout.addWidget(self.shuba_btn)
        
        self.booktoki_btn = QPushButton("3. booktoki için indirmeyi başlat")
        self.booktoki_btn.setEnabled(False)
        self.booktoki_btn.setStyleSheet("background-color: #9E9E9E; color: #E0E0E0; padding: 10px; border-radius: 5px;")
        self.booktoki_btn.clicked.connect(lambda: self.start_download("booktoki"))
        layout.addWidget(self.booktoki_btn)
        
        self.cancel_btn = QPushButton("İptal et")
        self.cancel_btn.setStyleSheet("margin-top: 10px; padding: 5px;")
        self.cancel_btn.clicked.connect(self.on_cancel_clicked)
        layout.addWidget(self.cancel_btn)
        
        # Durum bilgisi için etiket
        self.status_label = QLabel("Bekleniyor...")
        self.status_label.setStyleSheet("color: #4CAF50; font-style: italic; margin-top: 5px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        self.current_running_btn = None
        self.is_finished_signal_received = False # Çoklu uyarıyı engellemek için
        
        # Worker sinyallerini dinle
        self.worker.file_downloaded.connect(self.on_download_finished)
        self.worker.error.connect(self.on_download_error)
        if hasattr(self.worker, 'status_message'):
            self.worker.status_message.connect(self.update_status_label)

    def update_status_label(self, message):
        """Worker'dan gelen durum mesajını günceller."""
        self.status_label.setText(message)
        # Eğer mesajda "alınıyor" geçiyorsa sarı renkle vurgula
        if "alınıyor" in message.lower():
            self.status_label.setStyleSheet("color: #FFC107; font-weight: bold;")
        else:
            self.status_label.setStyleSheet("color: #4CAF50; font-style: italic;")

    def on_opened_clicked(self):
        """1. Bölüm açıldığında diğer butonları mavi ve aktif yapar."""
        app_logger.info("SeleniumMenuDialog: '1. Bölüm açıldı' tıklandı.")
        blue_style = "background-color: #2196F3; color: white; padding: 10px; font-weight: bold; border-radius: 5px;"
        self.shuba_btn.setEnabled(True)
        self.shuba_btn.setStyleSheet(blue_style)
        self.booktoki_btn.setEnabled(True)
        self.booktoki_btn.setStyleSheet(blue_style)
        
        self.opened_btn.setEnabled(False)
        self.opened_btn.setText("✅ Bölüm Hazır")
        self.opened_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 12px; font-weight: bold; border-radius: 5px;")
        
    def start_download(self, site):
        """İndirmeyi başlatır. Seçilen buton sarı, diğeri gri olur."""
        if site == "booktoki":
            count, ok = QInputDialog.getInt(self, "Bölüm Sayısı", "Kaç bölüm indirilecek?", self.worker.selenium_chapter_limit, 1, 10000)
            if not ok: return
            self.worker.selenium_chapter_limit = count
            self.current_running_btn = self.booktoki_btn
            other_btn = self.shuba_btn
        else:
            self.current_running_btn = self.shuba_btn
            other_btn = self.booktoki_btn

        # UI Güncelleme (Sarı: Çalışıyor, Gri: Devre Dışı)
        self.current_running_btn.setText("⏳ İndiriliyor...")
        self.current_running_btn.setStyleSheet("background-color: #FFC107; color: black; padding: 10px; font-weight: bold; border-radius: 5px;")
        self.current_running_btn.setEnabled(False)
        
        other_btn.setEnabled(False)
        other_btn.setStyleSheet("background-color: #9E9E9E; color: #E0E0E0; padding: 10px; border-radius: 5px;")
        
        # Worker'a komutu gönder
        app_logger.info(f"SeleniumMenuDialog: İndirme başlatılıyor: {site}")
        self.worker.selenium_command = site

    def on_download_finished(self, path, name):
        """İndirme bittiğinde butonu yeşil yapar."""
        if self.is_finished_signal_received:
            return
        self.is_finished_signal_received = True

        if self.current_running_btn:
            self.current_running_btn.setText("✅ Tamamlandı")
            self.current_running_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px; font-weight: bold; border-radius: 5px;")
        
        self.status_label.setText("✅ İşlem Başarıyla Tamamlandı")
        # QMessageBox.information(self, "Başarılı", f"İndirme tamamlandı:\n{name}") # Eski basit uyarı
        
        # Yeni aksiyon diyaloğunu aç
        post_dlg = PostDownloadDialog(path, name, self)
        post_dlg.exec()
        
        # Aksiyon bittikten sonra Selenium menüsünü de kapatabiliriz
        self.accept()

    def on_download_error(self, message):
        """Hata durumunda butonu eski haline getir veya uyar."""
        if self.current_running_btn:
            self.current_running_btn.setText("❌ Hata")
            self.current_running_btn.setStyleSheet("background-color: #F44336; color: white; padding: 10px; font-weight: bold; border-radius: 5px;")
        QMessageBox.critical(self, "Hata", f"İndirme sırasında hata oluştu:\n{message}")

    def on_cancel_clicked(self):
        app_logger.info("SeleniumMenuDialog: Kullanıcı iptal butonuna bastı.")
        self.worker.selenium_command = "cancel"
        self.reject()
