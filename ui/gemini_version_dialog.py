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
from core.localization import tr

# ─── V2.1.0 Geriye Uyumluluk Re-export'lar ───
# ui/ paketine taşınan sınıflar burada da erişilebilir kalır.
# Eski "from dialogs import X" çağrıları kırılmaz.
try:
    from ui.app_settings_dialog import AppSettingsDialog
    from ui.file_preview_dialog import FilePreviewDialog
except ImportError:
    pass  # ui paketi henüz mevcut değilse sessizce geç



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
    combobox.addItem(tr("new_project.combo_select", "Seçiniz..."), None)
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
        self.setWindowTitle(tr("gemini_version.window_title", "Gemini Model Versiyonu"))
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel(tr("gemini_version.select_or_enter", "Kullanılacak Gemini Model Versiyonunu Seçin veya Girin:")))
        
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
            models = [tr("gemini_version.manual_entry", "Manuel giriş yapınız...")]
            
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
             QMessageBox.warning(self, tr("main_window.msg_structure_error_title", "Hata"), tr("gemini_version.msg_version_empty", "Versiyon boş olamaz."))
             return

        if not self.config.has_section("Version"):
            self.config.add_section("Version")
        
        self.config.set("Version", "model_name", selected_version)
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                self.config.write(f)
            QMessageBox.information(self, tr("menu_bar.msg_save_success_title", "Başarılı"), tr("gemini_version.msg_save_success", "Versiyon kaydedildi."))
            self.accept()
        except Exception as e:
             QMessageBox.critical(self, tr("main_window.msg_structure_error_title", "Hata"), tr("gemini_version.msg_save_fail", "Kaydedilemedi: {}").format(e))
