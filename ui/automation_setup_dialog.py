"""
AutomationSetupDialog — Zincirleme İşlem (Workflow) ayar penceresi.

4 aşamalı yapılandırma:
  1. İndirme (Booktoki / 69shuba / Novelfire — Selenium)
  2. Prompt Üretme (Birebir / Doğal / Dengeli)
  3. Terminoloji Çıkarma
  4. Çeviri

Kullanıcı her aşamayı checkbox ile etkinleştirir/devre dışı bırakır.
"""

import os
import json
import configparser
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QCheckBox,
    QComboBox, QRadioButton, QSpinBox, QLabel, QPushButton,
    QFormLayout, QButtonGroup, QFrame, QSizePolicy
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
from logger import app_logger
from core.localization import tr


def _load_mcp_endpoints() -> list[dict]:
    """MCP_Endpoints.json'dan endpoint listesini yükler."""
    mcp_file = os.path.join(os.getcwd(), "AppConfigs", "MCP_Endpoints.json")
    endpoints = []
    if os.path.exists(mcp_file):
        try:
            with open(mcp_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            endpoints = data.get("endpoints", [])
        except Exception:
            pass
    return endpoints


def _get_chapter_count(project_path: str) -> int:
    """Projenin dwnld klasöründeki txt dosyası sayısını döndürür."""
    dwnld_dir = os.path.join(project_path, "dwnld")
    if not os.path.exists(dwnld_dir):
        return 0
    files = [f for f in os.listdir(dwnld_dir) if f.endswith(".txt")]
    return len(files)


def _get_last_terminology_op(project_path: str) -> tuple[int, int]:
    """Son terminoloji işlemi bölüm bilgisini okur."""
    config_path = os.path.join(project_path, "config", "config.ini")
    if not os.path.exists(config_path):
        return 0, 0
    cfg = configparser.ConfigParser()
    try:
        cfg.read(config_path, encoding="utf-8")
        s = cfg.getint("TerminologyOp", "last_start_chapter", fallback=0)
        e = cfg.getint("TerminologyOp", "last_end_chapter", fallback=0)
        return s, e
    except Exception:
        return 0, 0


def _make_separator() -> QFrame:
    """Yatay ayırıcı çizgi oluşturur."""
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFrameShadow(QFrame.Shadow.Sunken)
    line.setStyleSheet("color: #555;")
    return line


class AutomationSetupDialog(QDialog):
    """Zincirleme İşlem (Workflow) için 4 aşamalı ayar penceresi."""

    def __init__(self, project_name: str, project_path: str, parent=None):
        super().__init__(parent)
        self.project_name = project_name
        self.project_path = project_path
        self.setWindowTitle(tr("automation.window_title", "🚀 Tam Otomatik İşlem — {}").format(project_name))
        self.setMinimumWidth(520)
        self.setModal(True)

        # Proje config'ini oku
        self._config = configparser.ConfigParser()
        config_path = os.path.join(project_path, "config", "config.ini")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    self._config.read_file(f)
            except Exception:
                pass

        self._mcp_endpoints = _load_mcp_endpoints()
        self._chapter_count = _get_chapter_count(project_path)
        self._last_term_start, self._last_term_end = _get_last_terminology_op(project_path)

        self._build_ui()

    #  UI Oluşturma 

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # Başlık
        title = QLabel(tr("automation.title", "🚀 Tam Otomatik İşlem (Workflow)"))
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #FFB74D; margin-bottom: 4px;")
        layout.addWidget(title)

        subtitle = QLabel(tr("automation.subtitle", "Her aşamayı checkbox ile etkinleştirebilir veya atlayabilirsiniz."))
        subtitle.setFont(QFont("Segoe UI", 8))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #999; margin-bottom: 6px;")
        layout.addWidget(subtitle)

        #  Aşama 1: İndirme 
        self._build_download_stage(layout)
        layout.addWidget(_make_separator())

        #  Aşama 2: Prompt Üretme 
        self._build_prompt_stage(layout)
        layout.addWidget(_make_separator())

        #  Aşama 3: Terminoloji 
        self._build_terminology_stage(layout)
        layout.addWidget(_make_separator())

        #  Aşama 4: Çeviri 
        self._build_translation_stage(layout)

        #  Aksiyon Butonları 
        layout.addSpacing(8)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.start_btn = QPushButton(tr("automation.btn_start", "🚀 Başlat"))
        self.start_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.start_btn.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, "
            "stop:0 #FF6F00, stop:0.5 #AB47BC, stop:1 #7C4DFF);"
            "color: white; padding: 10px 28px; border-radius: 6px; "
            "border: 1px solid #FF8F00; font-size: 11pt;"
        )
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.clicked.connect(self._on_start)
        btn_layout.addWidget(self.start_btn)

        self.cancel_btn = QPushButton(tr("ml_range.btn_cancel", "İptal"))
        self.cancel_btn.setStyleSheet("padding: 10px 20px; border-radius: 6px;")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout)

    #  Aşama 1: İndirme 

    def _build_download_stage(self, parent_layout):
        self.download_check = QCheckBox(tr("automation.stage_1_download", "Aşama 1: İndirme"))
        self.download_check.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.download_check.setStyleSheet("color: #66BB6A;")
        self.download_check.setChecked(False)
        parent_layout.addWidget(self.download_check)

        self.download_group = QGroupBox()
        self.download_group.setEnabled(False)
        dl_form = QFormLayout(self.download_group)
        dl_form.setSpacing(6)

        # İndirme yöntemi
        self.download_method_combo = QComboBox()
        self.download_method_combo.addItem(tr("right_panel.download_method_booktoki", "Booktoki JS İle İndir (Selenium)"), "booktoki")
        self.download_method_combo.addItem(tr("right_panel.download_method_69shuba", "69shuba JS İle İndir (Selenium)"), "shuba")
        self.download_method_combo.addItem(tr("right_panel.download_method_novelfire", "Novelfire JS İle İndir (Selenium)"), "novelfire")
        self.download_method_combo.currentIndexChanged.connect(self._on_download_method_changed)
        dl_form.addRow(tr("right_panel.download_method", "İndirme Yöntemi:"), self.download_method_combo)

        # Bölüm sayısı (sadece Booktoki'de görünür)
        self.chapter_limit_label = QLabel(tr("automation.label_chapters_to_download", "İndirilecek Bölüm:"))
        self.chapter_limit_spin = QSpinBox()
        self.chapter_limit_spin.setMinimum(1)
        self.chapter_limit_spin.setMaximum(10000)
        self.chapter_limit_spin.setValue(120)
        dl_form.addRow(self.chapter_limit_label, self.chapter_limit_spin)

        parent_layout.addWidget(self.download_group)

        # Checkbox ↔ GroupBox bağlantısı
        self.download_check.toggled.connect(self.download_group.setEnabled)

        # Başlangıçta Booktoki seçili → bölüm sayısı görünür
        self._on_download_method_changed(0)

    def _on_download_method_changed(self, index):
        """Booktoki seçildiğinde bölüm sayısı alanını göster, diğerlerinde gizle."""
        is_booktoki = (index == 0)  # "Booktoki JS İle İndir (Selenium)"
        self.chapter_limit_label.setVisible(is_booktoki)
        self.chapter_limit_spin.setVisible(is_booktoki)

    #  Aşama 2: Prompt Üretme 

    def _build_prompt_stage(self, parent_layout):
        self.prompt_check = QCheckBox(tr("automation.stage_2_prompt", "Aşama 2: Prompt Üretme"))
        self.prompt_check.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.prompt_check.setStyleSheet("color: #42A5F5;")
        self.prompt_check.setChecked(True)
        parent_layout.addWidget(self.prompt_check)

        self.prompt_group = QGroupBox()
        self.prompt_group.setEnabled(True)
        pm_layout = QVBoxLayout(self.prompt_group)
        pm_layout.setSpacing(6)

        # Prompt tipi seçimi
        type_label = QLabel(tr("automation.label_prompt_type", "Ön Prompt Tipi:"))
        type_label.setFont(QFont("Segoe UI", 9))
        pm_layout.addWidget(type_label)

        self.prompt_type_group = QButtonGroup(self)
        type_layout = QHBoxLayout()
        self.radio_literal = QRadioButton(tr("automation.prompt_literal", "📖 Birebir (A)"))
        self.radio_natural = QRadioButton(tr("automation.prompt_natural", "💬 Doğal (B)"))
        self.radio_balanced = QRadioButton(tr("automation.prompt_balanced", "⚖️ Dengeli (C)"))
        self.radio_balanced.setChecked(True)

        self.prompt_type_group.addButton(self.radio_literal, 0)
        self.prompt_type_group.addButton(self.radio_natural, 1)
        self.prompt_type_group.addButton(self.radio_balanced, 2)
        type_layout.addWidget(self.radio_literal)
        type_layout.addWidget(self.radio_natural)
        type_layout.addWidget(self.radio_balanced)
        pm_layout.addLayout(type_layout)

        # API/MCP seçimi
        api_form = QFormLayout()
        self.prompt_api_combo = QComboBox()
        self._populate_api_combo(self.prompt_api_combo)
        api_form.addRow(tr("automation.label_api_mcp", "API / MCP:"), self.prompt_api_combo)
        pm_layout.addLayout(api_form)

        parent_layout.addWidget(self.prompt_group)
        self.prompt_check.toggled.connect(self.prompt_group.setEnabled)

    #  Aşama 3: Terminoloji 

    def _build_terminology_stage(self, parent_layout):
        self.terminology_check = QCheckBox(tr("automation.stage_3_terminology", "Aşama 3: Terminoloji Çıkarma"))
        self.terminology_check.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.terminology_check.setStyleSheet("color: #EC407A;")
        self.terminology_check.setChecked(True)
        parent_layout.addWidget(self.terminology_check)

        self.terminology_group = QGroupBox()
        self.terminology_group.setEnabled(True)
        term_form = QFormLayout(self.terminology_group)
        term_form.setSpacing(6)

        # Son bölüm — kullanıcı istediği değeri girebilir (indirme sonrası dosya sayısı bilinmeyebilir)
        self.term_end_spin = QSpinBox()
        self.term_end_spin.setMinimum(1)
        self.term_end_spin.setMaximum(99999)
        if self._chapter_count > 0:
            self.term_end_spin.setValue(self._chapter_count)
            self.term_end_spin.setSuffix(tr("automation.suffix_available", "  (Mevcut: {count})").format(count=self._chapter_count))
        else:
            self.term_end_spin.setValue(50)
            self.term_end_spin.setSuffix(tr("automation.suffix_no_files", "  (Henüz dosya yok)"))
        term_form.addRow(tr("automation.label_last_chapter", "Son Bölüm:"), self.term_end_spin)

        # API/MCP seçimi
        self.term_api_combo = QComboBox()
        self._populate_api_combo(self.term_api_combo)
        term_form.addRow(tr("automation.label_api_mcp", "API / MCP:"), self.term_api_combo)

        parent_layout.addWidget(self.terminology_group)
        self.terminology_check.toggled.connect(self.terminology_group.setEnabled)

    #  Aşama 4: Çeviri 

    def _build_translation_stage(self, parent_layout):
        self.translation_check = QCheckBox(tr("automation.stage_4_translation", "Aşama 4: Çeviri"))
        self.translation_check.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.translation_check.setStyleSheet("color: #FFA726;")
        self.translation_check.setChecked(True)
        parent_layout.addWidget(self.translation_check)

        self.translation_group = QGroupBox()
        self.translation_group.setEnabled(True)
        tr_layout = QVBoxLayout(self.translation_group)
        tr_layout.setSpacing(6)

        # Çeviri aralığı
        range_layout = QHBoxLayout()
        self.translate_all_radio = QRadioButton(tr("automation.translate_all", "Tamamını Çevir"))
        self.translate_all_radio.setChecked(True)
        self.translate_limit_radio = QRadioButton(tr("automation.translate_limit", "Sayılı Çevir:"))
        self.translate_limit_group = QButtonGroup(self)
        self.translate_limit_group.addButton(self.translate_all_radio, 0)
        self.translate_limit_group.addButton(self.translate_limit_radio, 1)

        self.translate_limit_spin = QSpinBox()
        self.translate_limit_spin.setMinimum(1)
        self.translate_limit_spin.setMaximum(99999)
        self.translate_limit_spin.setValue(20)
        self.translate_limit_spin.setEnabled(False)
        self.translate_limit_radio.toggled.connect(self.translate_limit_spin.setEnabled)

        range_layout.addWidget(self.translate_all_radio)
        range_layout.addWidget(self.translate_limit_radio)
        range_layout.addWidget(self.translate_limit_spin)
        range_layout.addStretch()
        tr_layout.addLayout(range_layout)

        # Detay ayarları
        detail_form = QFormLayout()
        detail_form.setSpacing(4)

        # API/MCP seçimi
        self.trans_api_combo = QComboBox()
        self._populate_api_combo(self.trans_api_combo)
        detail_form.addRow(tr("automation.label_api_mcp", "API / MCP:"), self.trans_api_combo)

        # Asenkron thread sayısı
        async_layout = QHBoxLayout()
        self.async_check = QCheckBox(tr("project_settings.checkbox_async", "Asenkron Çeviri"))
        self.async_check.setChecked(
            self._config.getboolean("Features", "async_enabled", fallback=False)
        )
        self.async_spin = QSpinBox()
        self.async_spin.setMinimum(1)
        self.async_spin.setMaximum(20)
        self.async_spin.setValue(
            self._config.getint("Features", "async_threads", fallback=3)
        )
        self.async_spin.setSuffix(tr("automation.suffix_thread", " thread"))
        self.async_check.toggled.connect(self.async_spin.setEnabled)
        self.async_spin.setEnabled(self.async_check.isChecked())
        async_layout.addWidget(self.async_check)
        async_layout.addWidget(self.async_spin)
        async_layout.addStretch()
        detail_form.addRow("", async_layout)

        # Batch ayarları
        batch_layout = QHBoxLayout()
        self.batch_check = QCheckBox(tr("project_settings.checkbox_batch", "Toplu Çeviri (Batch)"))
        self.batch_check.setChecked(
            self._config.getboolean("Batch", "batch_enabled", fallback=False)
        )
        self.batch_chars_spin = QSpinBox()
        self.batch_chars_spin.setMinimum(5000)
        self.batch_chars_spin.setMaximum(200000)
        self.batch_chars_spin.setSingleStep(1000)
        self.batch_chars_spin.setValue(
            self._config.getint("Batch", "max_batch_chars", fallback=33000)
        )
        self.batch_chars_spin.setSuffix(tr("automation.suffix_char", " karakter"))
        self.batch_check.toggled.connect(self.batch_chars_spin.setEnabled)
        self.batch_chars_spin.setEnabled(self.batch_check.isChecked())
        batch_layout.addWidget(self.batch_check)
        batch_layout.addWidget(self.batch_chars_spin)
        batch_layout.addStretch()
        detail_form.addRow("", batch_layout)

        tr_layout.addLayout(detail_form)
        parent_layout.addWidget(self.translation_group)
        self.translation_check.toggled.connect(self.translation_group.setEnabled)

    #  Yardımcı 

    def _populate_api_combo(self, combo: QComboBox):
        """API/MCP endpoint'lerini combobox'a doldurur."""
        combo.clear()

        # Proje varsayılanı
        project_mcp = self._config.get("MCP", "endpoint_id", fallback=None)
        project_api = self._config.get("API", "gemini_api_key", fallback=None)

        if project_mcp:
            combo.addItem(tr("automation.project_mcp_default", "📌 Proje MCP Varsayılanı"), {"type": "project_mcp", "id": project_mcp})
        elif project_api:
            combo.addItem(tr("automation.project_api_default", "📌 Proje API Varsayılanı"), {"type": "project_api", "key": project_api})

        # MCP Endpoint'leri
        for ep in self._mcp_endpoints:
            name = ep.get("name", ep.get("id", "?"))
            model = ep.get("model_id", "")
            combo.addItem(f"🔗 {name} ({model})", {"type": "mcp", "id": ep.get("id")})

    def _get_selected_api_config(self, combo: QComboBox) -> dict:
        """Seçili API/MCP konfigürasyonunu dict olarak döndürür."""
        data = combo.currentData()
        if data is None:
            return {}
        return data

    #  Sonuç 

    def _on_start(self):
        """Başlat butonuna basıldığında validasyon yap ve kabul et."""
        # En az bir aşama seçili mi?
        if not any([
            self.download_check.isChecked(),
            self.prompt_check.isChecked(),
            self.terminology_check.isChecked(),
            self.translation_check.isChecked()
        ]):
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, tr("automation.msg_no_stage_selected_title", "Aşama Seçilmedi"), tr("automation.msg_no_stage_selected_body", "Lütfen en az bir aşamayı etkinleştirin."))
            return
        self.accept()

    def get_config(self) -> dict:
        """Tüm workflow ayarlarını dict olarak döndürür."""
        prompt_type_map = {0: "A", 1: "B", 2: "C"}
        selected_prompt_type = prompt_type_map.get(
            self.prompt_type_group.checkedId(), "C"
        )

        download_site = self.download_method_combo.currentData() or "booktoki"

        return {
            # Genel
            "project_name": self.project_name,
            "project_path": self.project_path,

            # Aşama 1: İndirme
            "download_enabled": self.download_check.isChecked(),
            "download_site": download_site,
            "download_chapter_limit": self.chapter_limit_spin.value(),

            # Aşama 2: Prompt
            "prompt_enabled": self.prompt_check.isChecked(),
            "prompt_type": selected_prompt_type,  # "A", "B", "C"
            "prompt_api": self._get_selected_api_config(self.prompt_api_combo),

            # Aşama 3: Terminoloji
            "terminology_enabled": self.terminology_check.isChecked(),
            "terminology_end_chapter": self.term_end_spin.value(),
            "terminology_api": self._get_selected_api_config(self.term_api_combo),

            # Aşama 4: Çeviri
            "translation_enabled": self.translation_check.isChecked(),
            "translation_limit": (
                self.translate_limit_spin.value()
                if self.translate_limit_radio.isChecked()
                else None
            ),
            "translation_api": self._get_selected_api_config(self.trans_api_combo),
            "async_enabled": self.async_check.isChecked(),
            "async_threads": self.async_spin.value(),
            "batch_enabled": self.batch_check.isChecked(),
            "batch_max_chars": self.batch_chars_spin.value(),
        }
