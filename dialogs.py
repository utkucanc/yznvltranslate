import sys
import os
import configparser
from PyQt6.QtWidgets import (
    QDialog, QLineEdit, QFormLayout, QDialogButtonBox, 
    QMessageBox, QLabel, QApplication, QTextEdit, QListWidget, 
    QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QInputDialog
)
from PyQt6.QtGui import QIntValidator, QFont
from PyQt6.QtCore import Qt

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
        
        # Bilinen modeller
        models = [
            "gemini-2.5-flash-preview-09-2025",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
            "gemini-1.0-pro"
        ]
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
        
        layout.addRow("Proje Adı:", self.projectNameInput)
        layout.addRow("Proje Linki:", self.projectLinkInput)
        layout.addRow("Maksimum Sayfa:", self.maxPagesInput)
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
        
    def open_promt_editor(self):
        dlg = PromptEditorDialog(self)
        dlg.exec()
        self.refresh_combos()

    def get_data(self):
        max_pages_text = self.maxPagesInput.text()
        max_pages = int(max_pages_text) if max_pages_text.isdigit() else None
        return self.projectNameInput.text(), self.projectLinkInput.text(), max_pages, self.api_key_input.text(), self.startpromtinput.toPlainText()


class ProjectSettingsDialog(QDialog):
    """Mevcut proje ayarlarını düzenlemek için."""
    def __init__(self, project_name, project_link, max_pages, api_key, start_promt, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"'{project_name}' Ayarları")
        self.setMinimumWidth(500)
        layout = QFormLayout(self)

        self.projectNameLabel = QLabel(project_name)
        self.projectNameLabel.setStyleSheet("font-weight: bold;") 

        self.projectLinkInput = QLineEdit()
        self.projectLinkInput.setText(project_link)
        
        self.maxPagesInput = QLineEdit()
        if max_pages is not None:
            self.maxPagesInput.setText(str(max_pages))
        
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
        
        layout.addRow("Proje Adı:", self.projectNameLabel)
        layout.addRow("Proje Linki:", self.projectLinkInput)
        layout.addRow("Maksimum Sayfa:", self.maxPagesInput)
        layout.addRow("API Key Seç:", key_layout)
        layout.addRow("Mevcut API Key:", self.api_key_input)
        layout.addRow("Promt Seç:", promt_layout)
        layout.addRow("Promt İçeriği:", self.startpromtinput)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel, self)
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

    def open_promt_editor(self):
        dlg = PromptEditorDialog(self)
        dlg.exec()
        self.refresh_combos()

    def get_data(self):
        max_pages_text = self.maxPagesInput.text()
        max_pages = int(max_pages_text) if max_pages_text.isdigit() else None
        
        return {
            "link": self.projectLinkInput.text(),
            "max_pages": max_pages,
            "api_key": self.api_key_input.text(),
            "Startpromt": self.startpromtinput.toPlainText()
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