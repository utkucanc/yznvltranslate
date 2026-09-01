"""
new_project_dialog.py — Yeni Proje Oluştur diyaloğu (v2).

3-sütun tasarım (referans: novel_translator_pro2.py NewProjectDialog):
  Kolon 1: Temel Bilgiler (ad, link, maks sayfa/deneme, provider)
  Kolon 2: Proje Ayarları (Translation Style, model, workers slider, toggle'lar)
  Kolon 3: Gelişmiş (API Key, Prompt, MCP)

get_data() API'si DEĞİŞMEDİ — mevcut main_window.new_project_clicked() kırılmaz.
"""

import sys
import os
import configparser

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QComboBox, QSpinBox, QCheckBox,
    QSlider, QFrame, QWidget, QGroupBox, QApplication, QInputDialog
)
from PyQt6.QtGui import QIntValidator, QFont, QIcon
from PyQt6.QtCore import Qt, pyqtSignal, QObject

from logger import app_logger
from core.localization import tr

# --- V2.1.0 Geriye Uyumluluk Re-export'lar ---
try:
    from ui.app_settings_dialog import AppSettingsDialog
    from ui.file_preview_dialog import FilePreviewDialog
except ImportError:
    pass

# Re-export edilecek dialog sınıfları (dialogs.py'dan import edenler için)
try:
    from dialogs import (
        ApiKeyEditorDialog, PromptEditorDialog, MCPServerDialog
    )
except ImportError:
    try:
        from ui.api_key_editor_dialog import ApiKeyEditorDialog
        from ui.prompt_editor_dialog import PromptEditorDialog
        from ui.mcp_server_dialog import MCPServerDialog
    except ImportError:
        ApiKeyEditorDialog = None
        PromptEditorDialog = None
        MCPServerDialog = None

from ui.dark_theme import (
    BG_APP, BG_PANEL, BG_PANEL2, BORDER,
    TEXT_MAIN, TEXT_DIM, TEXT_FAINT,
    ACCENT_BLUE, ACCENT_GREEN, ACCENT_ORANGE, ACCENT_PURPLE
)


# ------------------------------------------------------------------
# Yardımcı fonksiyonlar (eski API korunuyor)
# ------------------------------------------------------------------

def get_config_path(subfolder: str) -> str:
    base_path = os.getcwd()
    path = os.path.join(base_path, "AppConfigs", subfolder)
    if not os.path.exists(path):
        os.makedirs(path)
    return path


def load_files_to_combo(combobox: QComboBox, subfolder: str):
    folder = get_config_path(subfolder)
    combobox.clear()
    combobox.addItem(tr("new_project.combo_select", "Seçiniz..."), None)
    if os.path.exists(folder):
        files = sorted([f for f in os.listdir(folder) if f.endswith(".txt")])
        for f in files:
            file_path = os.path.join(folder, f)
            try:
                with open(file_path, "r", encoding="utf-8") as fh:
                    content = fh.read().strip()
                combobox.addItem(f.replace(".txt", ""), content)
            except Exception:
                pass


# ------------------------------------------------------------------
# StyleCardGroup — Tekli seçim yöneticisi
# ------------------------------------------------------------------

class StyleCardGroup:
    def __init__(self):
        self.cards = []
        self.selected_value = "balanced"  # varsayılan

    def add_card(self, c):
        self.cards.append(c)

    def select(self, card):
        for c in self.cards:
            c.set_checked(c is card)
        self.selected_value = card.value


class StyleOptionCard(QFrame):
    """Translation Style seçim kartı."""

    def __init__(self, icon: str, title: str, sub: str,
                 group: StyleCardGroup, value: str, checked: bool = False):
        super().__init__()
        self.setObjectName("styleCardActive" if checked else "styleCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.value = value
        self._checked = checked

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(4)

        top = QHBoxLayout()
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(f"font-size:16px; color:{ACCENT_BLUE};")
        top.addWidget(icon_lbl)
        top.addStretch()
        self.check_dot = QLabel("●")
        self.check_dot.setStyleSheet(f"color:{ACCENT_BLUE};")
        self.check_dot.setVisible(checked)
        top.addWidget(self.check_dot)
        lay.addLayout(top)

        t = QLabel(title)
        t.setStyleSheet(f"color:{TEXT_MAIN}; font-size:12px; font-weight:700;")
        lay.addWidget(t)

        s = QLabel(sub)
        s.setWordWrap(True)
        s.setStyleSheet(f"color:{TEXT_FAINT}; font-size:10px;")
        lay.addWidget(s)

        self.group = group
        group.add_card(self)
        if checked:
            group.selected_value = value

    def set_checked(self, val: bool):
        self._checked = val
        self.check_dot.setVisible(val)
        self.setObjectName("styleCardActive" if val else "styleCard")
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event):
        self.group.select(self)


class ToggleSwitch(QCheckBox):
    def __init__(self, checked: bool = True):
        super().__init__()
        self.setChecked(checked)
        self.setObjectName("toggleSwitch")
        self.setFixedSize(38, 20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)


# ------------------------------------------------------------------
# Ana Dialog
# ------------------------------------------------------------------

class NewProjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("new_project.window_title", "Yeni Proje Oluştur"))
        self.setModal(True)
        self.setMinimumSize(1020, 660)
        self.resize(1060, 700)

        self.style_group = StyleCardGroup()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        panel = QFrame()
        panel.setObjectName("card")
        outer.addWidget(panel)

        lay = QVBoxLayout(panel)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(16)

        # -- Başlık --
        header = QHBoxLayout()
        icon_lbl = QLabel("📁")
        icon_lbl.setStyleSheet(
            f"background:{ACCENT_BLUE}22; color:{ACCENT_BLUE}; "
            f"border-radius:8px; font-size:16px; padding:6px 10px;"
        )
        header.addWidget(icon_lbl)
        title_lbl = QLabel(tr("new_project.window_title", "Yeni Proje Oluştur"))
        title_lbl.setStyleSheet(f"color:{TEXT_MAIN}; font-size:17px; font-weight:700;")
        header.addWidget(title_lbl)
        header.addStretch()
        close_btn = QPushButton("✕")
        close_btn.setObjectName("iconBtn")
        close_btn.clicked.connect(self.reject)
        header.addWidget(close_btn)
        lay.addLayout(header)

        # -- 3 Sütun --
        cols = QHBoxLayout()
        cols.setSpacing(20)
        cols.addLayout(self._build_column1(), 1)
        cols.addWidget(self._vline())
        cols.addLayout(self._build_column2(), 1)
        cols.addWidget(self._vline())
        cols.addLayout(self._build_column3(), 1)
        lay.addLayout(cols, 1)

        # -- Footer --
        footer = QHBoxLayout()
        footer.addStretch()
        cancel_btn = QPushButton(tr("new_project.btn_cancel", "İptal"))
        cancel_btn.setObjectName("smallBtn")
        cancel_btn.clicked.connect(self.reject)
        create_btn = QPushButton("+  " + tr("new_project.btn_create", "Proje Oluştur"))
        create_btn.setObjectName("primaryBtn")
        create_btn.clicked.connect(self.accept)
        footer.addWidget(cancel_btn)
        footer.addWidget(create_btn)
        lay.addLayout(footer)

    # ------------------------------------------------------------------
    # Sütun 1: Temel Bilgiler
    # ------------------------------------------------------------------

    def _build_column1(self) -> QVBoxLayout:
        col = QVBoxLayout()
        col.setSpacing(8)
        col.addWidget(self._section_title("1. " + tr("new_project.col1_title", "Temel Bilgiler")))

        # Proje adı
        col.addWidget(self._field_label(tr("new_project.label_project_name", "Proje Adı")))
        self.projectNameInput = QLineEdit()
        self.projectNameInput.setPlaceholderText(tr("new_project_extra.placeholder_project_name", "Proje adını girin..."))
        col.addWidget(self.projectNameInput)

        # URL
        col.addWidget(self._field_label(tr("new_project.label_project_link", "Proje Linki / URL")))
        self.projectLinkInput = QLineEdit()
        self.projectLinkInput.setPlaceholderText(tr("new_project_extra.placeholder_project_link", "https://..."))
        col.addWidget(self.projectLinkInput)

        # Maks sayfa
        col.addWidget(self._field_label(tr("new_project.label_max_pages", "Maksimum Sayfa (isteğe bağlı)")))
        self.maxPagesInput = QLineEdit()
        self.maxPagesInput.setValidator(QIntValidator(1, 999999))
        self.maxPagesInput.setPlaceholderText(tr("new_project_extra.placeholder_max_pages", "Boş bırakın = sınırsız"))
        col.addWidget(self.maxPagesInput)

        # Maks deneme
        col.addWidget(self._field_label(tr("new_project.label_max_retries", "Maksimum Deneme")))
        self.maxRetriesInput = QSpinBox()
        self.maxRetriesInput.setMinimum(1)
        self.maxRetriesInput.setMaximum(20)
        self.maxRetriesInput.setValue(3)
        self.maxRetriesInput.setToolTip(tr("new_project_extra.tooltip_max_retries", "API hatasında tekrar deneme sayısı"))
        col.addWidget(self.maxRetriesInput)

        # Çeviri sağlayıcısı
        col.addWidget(self._field_label(tr("project_settings.label_provider_select", "Çeviri Sağlayıcısı")))
        self.provider_combo = QComboBox()
        self.provider_combo.addItem(tr("project_settings.provider_llm", "Yapay Zeka (LLM / MCP)"), "llm")
        self.provider_combo.addItem(tr("project_settings.provider_google", "Google Translate (Ücretsiz)"), "google")
        self.provider_combo.addItem(tr("project_settings.provider_yandex", "Yandex Translate (Ücretsiz)"), "yandex")
        self.provider_combo.currentIndexChanged.connect(self.on_provider_changed)
        col.addWidget(self.provider_combo)

        col.addStretch()
        return col

    # ------------------------------------------------------------------
    # Sütun 2: Proje Ayarları
    # ------------------------------------------------------------------

    def _build_column2(self) -> QVBoxLayout:
        col = QVBoxLayout()
        col.setSpacing(8)
        col.addWidget(self._section_title("2. " + tr("new_project.col2_title", "Proje Ayarları")))

        # Translation Style
        col.addWidget(self._field_label(tr("new_project.label_translation_style", "Çeviri Stili")))
        style_row = QHBoxLayout()
        style_row.setSpacing(8)
        style_row.addWidget(
            StyleOptionCard("⇄", "Literal", "Kelime kelime doğru çeviri.", self.style_group, "literal")
        )
        style_row.addWidget(
            StyleOptionCard("⚖", "Balanced", "Doğruluk ve okunabilirlik dengesi.", self.style_group, "balanced", checked=True)
        )
        style_row.addWidget(
            StyleOptionCard("🍃", "Natural", "Doğal ve akıcı çeviri.", self.style_group, "natural")
        )
        col.addLayout(style_row)

        # Model
        col.addWidget(self._field_label(tr("new_project.label_model", "Varsayılan Model")))
        self.model_combo = QComboBox()
        self._populate_models()
        col.addWidget(self.model_combo)
        col.addWidget(self._hint_label("Proje ayarlarından daha sonra değiştirilebilir."))

        # Parallel Workers slider
        workers_hdr = QHBoxLayout()
        workers_hdr.addWidget(self._field_label(tr("new_project.label_parallel_workers", "Paralel Worker")))
        workers_hdr.addStretch()
        self._workers_val_lbl = QLabel("3")
        self._workers_val_lbl.setStyleSheet(f"color:{TEXT_MAIN}; font-size:12px; font-weight:700;")
        workers_hdr.addWidget(self._workers_val_lbl)
        col.addLayout(workers_hdr)

        self.workers_slider = QSlider(Qt.Orientation.Horizontal)
        self.workers_slider.setMinimum(1)
        self.workers_slider.setMaximum(10)
        self.workers_slider.setValue(3)
        self.workers_slider.valueChanged.connect(
            lambda v: self._workers_val_lbl.setText(str(v))
        )
        col.addWidget(self.workers_slider)

        minmax = QHBoxLayout()
        l1 = QLabel("1"); l1.setStyleSheet(f"color:{TEXT_FAINT}; font-size:10px;")
        l2 = QLabel("10"); l2.setStyleSheet(f"color:{TEXT_FAINT}; font-size:10px;")
        minmax.addWidget(l1); minmax.addStretch(); minmax.addWidget(l2)
        col.addLayout(minmax)
        col.addWidget(self._hint_label("Öneri: Gemini için 3 (RPM: 11-12)"))

        # Toggle switch'ler
        col.addLayout(self._toggle_row(
            "Batch Mode",
            "Birden fazla bölümü tek istekte paketler (kota tasarrufu).",
            False
        ))
        col.addLayout(self._toggle_row(
            "Translation Cache",
            "Otomatik cache aktif — maliyet ve hız iyileştirir.",
            True
        ))
        col.addLayout(self._toggle_row(
            "Quality Check",
            "Benzerlik kontrolü, dil tespiti ve CJK taraması.",
            True
        ))

        col.addStretch()
        return col

    # ------------------------------------------------------------------
    # Sütun 3: Gelişmiş (API Key, Prompt, MCP)
    # ------------------------------------------------------------------

    def _build_column3(self) -> QVBoxLayout:
        col = QVBoxLayout()
        col.setSpacing(8)
        col.addWidget(self._section_title("3. " + tr("new_project.col3_title", "Bağlantı & Gelişmiş")))

        # API Key
        col.addWidget(self._field_label(tr("new_project.label_api_key_select", "API Key Seç")))
        key_row = QHBoxLayout()
        self.api_key_combo = QComboBox()
        self.api_key_combo.currentIndexChanged.connect(self.on_api_combo_changed)
        key_row.addWidget(self.api_key_combo, 1)
        if ApiKeyEditorDialog:
            self.edit_keys_btn = QPushButton(tr("app_settings.btn_edit", "Düzenle"))
            self.edit_keys_btn.setObjectName("smallBtn")
            self.edit_keys_btn.setFixedWidth(60)
            self.edit_keys_btn.clicked.connect(self.open_key_editor)
            key_row.addWidget(self.edit_keys_btn)
        col.addLayout(key_row)

        col.addWidget(self._field_label(tr("new_project.label_selected_api_key", "Seçili API Key")))
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText(tr("new_project.placeholder_api_key", "Manuel giriş veya listeden seçin..."))
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        col.addWidget(self.api_key_input)

        # Prompt
        col.addWidget(self._field_label(tr("new_project.label_prompt_select", "Prompt Seç")))
        promt_row = QHBoxLayout()
        self.promt_combo = QComboBox()
        self.promt_combo.currentIndexChanged.connect(self.on_promt_combo_changed)
        promt_row.addWidget(self.promt_combo, 1)
        if PromptEditorDialog:
            self.edit_promt_btn = QPushButton(tr("app_settings.btn_edit", "Düzenle"))
            self.edit_promt_btn.setObjectName("smallBtn")
            self.edit_promt_btn.setFixedWidth(60)
            self.edit_promt_btn.clicked.connect(self.open_promt_editor)
            promt_row.addWidget(self.edit_promt_btn)
        col.addLayout(promt_row)

        col.addWidget(self._field_label(tr("new_project.label_prompt_content", "Prompt İçeriği")))
        self.startpromtinput = QTextEdit()
        self.startpromtinput.setPlaceholderText(
            "Seçilen veya manuel girilen prompt metni buraya gelecek...\n"
            "(Prompt seçerek veya Prompt Editörü'nden seçebilirsiniz)"
        )
        self.startpromtinput.setMinimumHeight(110)
        self.startpromtinput.setMaximumHeight(180)
        col.addWidget(self.startpromtinput)

        # MCP Endpoint
        mcp_group = QGroupBox(tr("new_project.group_mcp", "Yapay Zeka Kaynağı (MCP)"))
        mcp_lay = QVBoxLayout()
        self.use_custom_endpoint = QCheckBox(tr("new_project.checkbox_custom_mcp", "Bu proje için özel bağlantı kullan"))
        mcp_lay.addWidget(self.use_custom_endpoint)

        ep_row = QHBoxLayout()
        self.endpoint_combo = QComboBox()
        self.endpoint_combo.setEnabled(False)
        self._load_endpoints()
        ep_row.addWidget(self.endpoint_combo, 1)

        if MCPServerDialog:
            self.mcp_manage_btn = QPushButton(tr("new_project.btn_mcp_manage", "MCP Yönet"))
            self.mcp_manage_btn.setObjectName("smallBtn")
            self.mcp_manage_btn.setFixedWidth(100)
            self.mcp_manage_btn.clicked.connect(self.open_mcp_dialog)
            ep_row.addWidget(self.mcp_manage_btn)
        mcp_lay.addLayout(ep_row)
        mcp_group.setLayout(mcp_lay)
        self.use_custom_endpoint.toggled.connect(self.endpoint_combo.setEnabled)
        col.addWidget(mcp_group)

        col.addStretch()

        # Combolar yükle ve provider durumu güncelle
        self.refresh_combos()
        self.on_provider_changed()

        return col

    # ------------------------------------------------------------------
    # Yardımcı widget üreticiler
    # ------------------------------------------------------------------

    def _section_title(self, text: str) -> QLabel:
        l = QLabel(text)
        l.setStyleSheet(f"color:{TEXT_MAIN}; font-size:13px; font-weight:700;")
        return l

    def _field_label(self, text: str) -> QLabel:
        l = QLabel(text)
        l.setStyleSheet(f"color:{TEXT_DIM}; font-size:11px;")
        return l

    def _hint_label(self, text: str) -> QLabel:
        l = QLabel(text)
        l.setWordWrap(True)
        l.setStyleSheet(f"color:{TEXT_FAINT}; font-size:10px;")
        return l

    def _vline(self) -> QFrame:
        v = QFrame()
        v.setFrameShape(QFrame.Shape.VLine)
        v.setStyleSheet(f"color: {BORDER};")
        return v

    def _toggle_row(self, title: str, sub: str, checked: bool) -> QVBoxLayout:
        row = QVBoxLayout()
        row.setSpacing(2)
        top = QHBoxLayout()
        t = QLabel(title)
        t.setStyleSheet(f"color:{TEXT_MAIN}; font-size:12px; font-weight:600;")
        top.addWidget(t)
        top.addStretch()
        sw = ToggleSwitch(checked)
        # Toggle'ları kaydet (get_data için)
        setattr(self, f"_toggle_{title.lower().replace(' ', '_').replace('(', '').replace(')', '')}", sw)
        top.addWidget(sw)
        row.addLayout(top)
        row.addWidget(self._hint_label(sub))
        return row

    # ------------------------------------------------------------------
    # Slot'lar
    # ------------------------------------------------------------------

    def on_provider_changed(self):
        prov = self.provider_combo.currentData()
        is_llm = (prov == "llm")
        self.api_key_combo.setEnabled(is_llm)
        self.api_key_input.setEnabled(is_llm or prov == "yandex")
        if hasattr(self, 'edit_keys_btn'):
            self.edit_keys_btn.setEnabled(is_llm)
        self.promt_combo.setEnabled(is_llm)
        if hasattr(self, 'edit_promt_btn'):
            self.edit_promt_btn.setEnabled(is_llm)
        self.startpromtinput.setEnabled(is_llm)
        self.use_custom_endpoint.setEnabled(is_llm)
        self.endpoint_combo.setEnabled(is_llm and self.use_custom_endpoint.isChecked())
        if hasattr(self, 'mcp_manage_btn'):
            self.mcp_manage_btn.setEnabled(is_llm)

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
        if ApiKeyEditorDialog:
            dlg = ApiKeyEditorDialog(self)
            dlg.exec()
            self.refresh_combos()

    def _load_endpoints(self, selected_id=None):
        self.endpoint_combo.clear()
        self.endpoint_combo.addItem(tr("new_project.combo_global_endpoint", "Global Aktif Endpoint"), None)
        try:
            from core.llm_provider import load_endpoints
            data = load_endpoints()
            for ep in data.get("endpoints", []):
                self.endpoint_combo.addItem(f"{ep['name']} ({ep['type']})", ep["id"])
                if selected_id and ep["id"] == selected_id:
                    self.endpoint_combo.setCurrentIndex(self.endpoint_combo.count() - 1)
        except Exception:
            pass

    def open_mcp_dialog(self):
        if MCPServerDialog:
            dlg = MCPServerDialog(self)
            dlg.exec()
            current_id = self.endpoint_combo.currentData()
            self._load_endpoints(current_id)

    def open_promt_editor(self):
        if PromptEditorDialog:
            dlg = PromptEditorDialog(self)
            dlg.exec()
            self.refresh_combos()

    def _populate_models(self):
        """Mevcut model listesini doldurur."""
        models = [
            "gemini-2.5-flash", "gemini-2.5-pro",
            "gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash",
        ]
        # Mevcut modeli en başa al
        try:
            cfg_path = os.path.join(os.getcwd(), "AppConfigs", "GVersion.ini")
            cfg = configparser.ConfigParser()
            if os.path.exists(cfg_path):
                cfg.read(cfg_path)
                current = cfg.get("Version", "model_name", fallback="gemini-2.5-flash")
                if current in models:
                    models.remove(current)
                models.insert(0, current)
        except Exception:
            pass
        self.model_combo.addItems(models)

    # ------------------------------------------------------------------
    # Veri döndürme (ESKİ API — main_window.new_project_clicked() kırılmaz)
    # ------------------------------------------------------------------

    def get_data(self):
        """
        Döndürür:
            (project_name, project_link, max_pages, max_retries,
             api_key, startpromt, api_key_name, mcp_endpoint_id, translation_provider)
        """
        max_pages_text = self.maxPagesInput.text()
        max_pages = int(max_pages_text) if max_pages_text.isdigit() else None

        api_key_name = self.api_key_combo.currentText()
        if api_key_name == tr("new_project.combo_select", "Seçiniz..."):
            api_key_name = ""

        mcp_endpoint_id = None
        if self.use_custom_endpoint.isChecked():
            mcp_endpoint_id = self.endpoint_combo.currentData()

        return (
            self.projectNameInput.text(),
            self.projectLinkInput.text(),
            max_pages,
            self.maxRetriesInput.value(),
            self.api_key_input.text(),
            self.startpromtinput.toPlainText(),
            api_key_name,
            mcp_endpoint_id,
            self.provider_combo.currentData(),
        )
