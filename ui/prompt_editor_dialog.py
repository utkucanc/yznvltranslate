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


class PromptEditorDialog(QDialog):
    """Kayıtlı Promtları düzenlemek için."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("prompt_editor.window_title", "Promt Editörü"))
        self.resize(800, 600)
        self.prompts_folder = get_config_path("Promts")

        # Ana Düzen
        main_layout = QHBoxLayout(self)

        # --- Sol Panel (Liste) ---
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel(tr("prompt_editor.saved_prompts", "Kayıtlı Promtlar:")))
        
        self.prompt_list_widget = QListWidget()
        self.prompt_list_widget.currentItemChanged.connect(self.on_prompt_selected)
        left_layout.addWidget(self.prompt_list_widget)

        # Yeni ve Sil Butonları
        button_layout = QHBoxLayout()
        self.new_btn = QPushButton(tr("prompt_editor.btn_new", "Yeni"))
        self.new_btn.clicked.connect(self.new_prompt)
        self.delete_btn = QPushButton(tr("prompt_editor.btn_delete", "Sil"))
        self.delete_btn.setStyleSheet("color: red;")
        self.delete_btn.clicked.connect(self.delete_prompt)
        button_layout.addWidget(self.new_btn)
        button_layout.addWidget(self.delete_btn)
        left_layout.addLayout(button_layout)

        # --- Sağ Panel (Editör) ---
        right_layout = QVBoxLayout()
        
        form_layout = QFormLayout()
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText(tr("prompt_editor.placeholder_title", "Promt Başlığı (Dosya Adı)"))
        form_layout.addRow(tr("prompt_editor.label_title", "Başlık:"), self.title_input)
        right_layout.addLayout(form_layout)
        
        right_layout.addWidget(QLabel(tr("prompt_editor.prompt_content", "Promt İçeriği:")))
        self.content_edit = QTextEdit()
        right_layout.addWidget(self.content_edit)

        # Kaydet Butonu
        self.save_btn = QPushButton(tr("prompt_editor.btn_save", "Kaydet"))
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
                QMessageBox.warning(self, tr("main_window.msg_structure_error_title", "Hata"), tr("prompt_editor.msg_read_error", "Dosya okunamadı: {}").format(e))

    def new_prompt(self):
        self.prompt_list_widget.clearSelection()
        self.title_input.clear()
        self.content_edit.clear()
        self.title_input.setFocus()

    def save_prompt(self):
        title = self.title_input.text().strip()
        content = self.content_edit.toPlainText()

        if not title:
            QMessageBox.warning(self, tr("prompt_editor.msg_missing_title", "Eksik"), tr("prompt_editor.msg_missing_body", "Lütfen bir başlık giriniz."))
            return

        safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '-', '_')]).strip()
        if not safe_title:
             QMessageBox.warning(self, tr("prompt_editor.msg_invalid_title", "Geçersiz"), tr("prompt_editor.msg_invalid_body", "Başlık geçersiz karakterler içeriyor."))
             return

        new_filename = safe_title + ".txt"
        new_filepath = os.path.join(self.prompts_folder, new_filename)

        try:
            with open(new_filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            QMessageBox.information(self, tr("menu_bar.msg_save_success_title", "Başarılı"), tr("prompt_editor.msg_save_success", "Promt kaydedildi."))
            self.load_prompts()
            items = self.prompt_list_widget.findItems(safe_title, Qt.MatchFlag.MatchExactly)
            if items:
                self.prompt_list_widget.setCurrentItem(items[0])
                
        except Exception as e:
            QMessageBox.critical(self, tr("main_window.msg_structure_error_title", "Hata"), tr("prompt_editor.msg_save_fail", "Kaydetme başarısız: {}").format(e))

    def delete_prompt(self):
        current_item = self.prompt_list_widget.currentItem()
        if not current_item:
            return

        title = current_item.text()
        filename = title + ".txt"
        filepath = os.path.join(self.prompts_folder, filename)

        reply = QMessageBox.question(self, tr("prompt_editor.delete_confirm_title", "Sil"), tr("prompt_editor.delete_confirm_body", "'{}' promtunu silmek istediğinize emin misiniz?").format(title),
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
                    self.load_prompts()
                    self.new_prompt() 
            except Exception as e:
                QMessageBox.critical(self, tr("main_window.msg_structure_error_title", "Hata"), tr("prompt_editor.msg_delete_fail", "Silme başarısız: {}").format(e))
