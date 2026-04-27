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
try:
    from ui.app_settings_dialog import AppSettingsDialog
    from ui.file_preview_dialog import FilePreviewDialog
    from ui.prompt_editor_dialog import PromptEditorDialog
    from ui.api_key_editor_dialog import ApiKeyEditorDialog
    from ui.mcp_server_dialog import MCPServerDialog
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


class NewProjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Yeni Proje Oluştur")
        self.setMinimumWidth(520)
        self.resize(560, 620)
        layout = QFormLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        
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
        self.startpromtinput.setPlaceholderText(
            "Seçilen veya manuel girilen prompt metni buraya gelecek...\n"
            "(Prompt seçenerek veya Prompt Editörü'nden seçebilirsiniz)"
        )
        self.startpromtinput.setMinimumHeight(120)
        self.startpromtinput.setMaximumHeight(200)
        
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
