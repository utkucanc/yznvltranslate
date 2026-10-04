from core.path_resolver import get_project_dir
import sys
import os
import configparser
from PyQt6.QtWidgets import (
    QDialog, QLineEdit, QFormLayout, QDialogButtonBox,
    QMessageBox, QLabel, QApplication, QTextEdit, QListWidget,
    QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QInputDialog,
    QSpinBox, QCheckBox, QGroupBox, QSplitter, QWidget, QProgressBar,
    QScrollArea, QSizePolicy, QFrame
)
from PyQt6.QtGui import QIntValidator, QFont, QIcon, QAction
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject, QSize
from logger import app_logger
from core.localization import tr
from ui.dark_theme import (
    BG_APP, BG_PANEL, BG_PANEL2, BORDER,
    TEXT_MAIN, TEXT_DIM, TEXT_FAINT,
    ACCENT_BLUE, ACCENT_GREEN, ACCENT_ORANGE, ACCENT_PURPLE
)

# --- V2.1.0 Geriye Uyumluluk Re-export'lar ---
try:
    from ui.file_preview_dialog import FilePreviewDialog
    from ui.terminology_dialog import TerminologyDialog
    from ui.prompt_editor_dialog import PromptEditorDialog
    from ui.api_key_editor_dialog import ApiKeyEditorDialog
    from ui.mcp_server_dialog import MCPServerDialog
except ImportError:
    pass


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
                combobox.addItem(f.replace('.txt', ''), content)
            except:
                pass


class ProjectSettingsDialog(QDialog):
    """Mevcut proje ayarlarını düzenleme penceresi — 3 kolonlu yatay tasarım."""

    def __init__(self, project_name, project_link, max_pages, api_key, start_promt,
                 gemini_version, deepl_api, yandex_api, parent=None,
                 mcp_endpoint_id=None, terminology_enabled=True,
                 async_enabled=False, async_threads=3,
                 batch_enabled=False, max_batch_chars=33000, max_chapters_per_batch=5,
                 translation_provider="llm", source_lang=None):
        super().__init__(parent)
        self.setWindowTitle(
            tr("project_settings.window_title", "'{}' Ayarları").format(project_name)
        )
        self.setModal(True)
        self.setMinimumSize(1020, 660)
        self.resize(1080, 720)
        self.project_name = project_name

        # Dil listesi
        _LANG_CODES = [
            ('en', tr('languages.en', 'İngilizce (en)')),
            ('ko', tr('languages.ko', 'Korece (ko)')),
            ('zh-cn', tr('languages.zh_cn', 'Çince Basitleştirilmiş (zh-cn)')),
            ('zh-tw', tr('languages.zh_tw', 'Çince Geleneksel (zh-tw)')),
            ('ja', tr('languages.ja', 'Japonca (ja)')),
            ('tr', tr('languages.tr', 'Türkçe (tr)')),
            ('de', tr('languages.de', 'Almanca (de)')),
            ('fr', tr('languages.fr', 'Fransızca (fr)')),
            ('es', tr('languages.es', 'İspanyolca (es)')),
        ]

        # Kaynak dil varsayılanı
        if not source_lang:
            try:
                from ui.app_settings_dialog import load_app_settings
                source_lang = load_app_settings().get('langdetect_source_lang', 'en')
            except Exception:
                source_lang = 'en'

        #  Dış layout
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        panel = QFrame()
        panel.setObjectName('card')
        outer.addWidget(panel)

        lay = QVBoxLayout(panel)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(16)

        # Başlık
        header = QHBoxLayout()
        icon_lbl = QLabel('⚙')
        icon_lbl.setStyleSheet(
            f'background:{ACCENT_BLUE}22; color:{ACCENT_BLUE};'
            ' border-radius:8px; font-size:16px; padding:6px 10px;'
        )
        header.addWidget(icon_lbl)
        title_lbl = QLabel(
            tr("project_settings.window_title", "'{}' Ayarları").format(project_name)
        )
        title_lbl.setStyleSheet(f'color:{TEXT_MAIN}; font-size:17px; font-weight:700;')
        header.addWidget(title_lbl)
        header.addStretch()
        close_btn = QPushButton('✕')
        close_btn.setObjectName('iconBtn')
        close_btn.clicked.connect(self.reject)
        header.addWidget(close_btn)
        lay.addLayout(header)

        # 3 Kolon
        cols = QHBoxLayout()
        cols.setSpacing(20)
        cols.addLayout(self._build_column1(
            project_name, project_link, max_pages,
            translation_provider, deepl_api, yandex_api,
            _LANG_CODES, source_lang, parent
        ), 1)
        cols.addWidget(self._vline())
        cols.addLayout(self._build_column2(
            api_key, mcp_endpoint_id,
            async_enabled, async_threads,
            batch_enabled, max_batch_chars, max_chapters_per_batch,
            terminology_enabled
        ), 1)
        cols.addWidget(self._vline())
        cols.addLayout(self._build_column3(start_promt), 1)
        lay.addLayout(cols, 1)

        # Footer butonlar
        footer = QHBoxLayout()
        footer.addStretch()
        cancel_btn = QPushButton(tr('new_project.btn_cancel', 'İptal'))
        cancel_btn.setObjectName('smallBtn')
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton('💾  ' + tr('project_settings.btn_save', 'Kaydet'))
        save_btn.setObjectName('primaryBtn')
        save_btn.clicked.connect(self.accept)
        footer.addWidget(cancel_btn)
        footer.addWidget(save_btn)
        lay.addLayout(footer)

        # Combolar yükle & provider görünürlüğü
        self.refresh_combos()
        self.on_provider_changed()

    # Kolon 1: Temel Bilgiler + Provider
    def _build_column1(self, project_name, project_link, max_pages,
                       translation_provider, deepl_api, yandex_api,
                       lang_codes, source_lang, parent):
        col = QVBoxLayout()
        col.setSpacing(8)
        col.addWidget(self._section_title('1. ' + tr('new_project.col1_title', 'Temel Bilgiler')))

        col.addWidget(self._field_label(tr('project_settings.label_project_name', 'Proje Adı')))
        name_lbl = QLabel(project_name)
        name_lbl.setStyleSheet(f'color:{TEXT_MAIN}; font-weight:600;')
        col.addWidget(name_lbl)
        self.projectNameLabel = name_lbl

        col.addWidget(self._field_label(tr('project_settings.label_project_link', 'Proje Linki')))
        self.projectLinkInput = QLineEdit()
        self.projectLinkInput.setText(project_link)
        col.addWidget(self.projectLinkInput)

        col.addWidget(self._field_label(tr('project_settings.label_max_pages', 'Maks. Sayfa')))
        self.maxPagesInput = QLineEdit()
        if max_pages is not None:
            self.maxPagesInput.setText(str(max_pages))
        col.addWidget(self.maxPagesInput)

        col.addWidget(self._field_label(tr('project_settings.label_max_retries', 'Maks. Deneme')))
        self.maxRetriesInput = QSpinBox()
        self.maxRetriesInput.setMinimum(1)
        self.maxRetriesInput.setMaximum(20)
        self.maxRetriesInput.setValue(parent.max_retries if hasattr(parent, 'max_retries') else 3)
        col.addWidget(self.maxRetriesInput)

        col.addWidget(self._field_label(tr('project_settings.label_provider_select', 'Çeviri Sağlayıcısı')))
        self.provider_combo = QComboBox()
        self.provider_combo.addItem(tr('project_settings.provider_llm', 'Yapay Zeka (LLM / MCP)'), 'llm')
        self.provider_combo.addItem(tr('project_settings.provider_google', 'Google Translate (Ücretsiz)'), 'google')
        self.provider_combo.addItem(tr('project_settings.provider_yandex', 'Yandex Translate (Ücretsiz)'), 'yandex')
        self.provider_combo.addItem(tr('project_settings.provider_deepl', 'DeepL Translate (Ücretli)'), 'deepl')
        idx = self.provider_combo.findData(translation_provider)
        if idx >= 0:
            self.provider_combo.setCurrentIndex(idx)
        self.provider_combo.currentIndexChanged.connect(self.on_provider_changed)
        col.addWidget(self.provider_combo)

        col.addWidget(self._field_label(tr('project_settings.label_source_lang', 'Kaynak Dil')))
        self.source_lang_combo = QComboBox()
        for code, label in lang_codes:
            self.source_lang_combo.addItem(label, code)
        all_codes = [self.source_lang_combo.itemData(i) for i in range(self.source_lang_combo.count())]
        src_idx = all_codes.index(source_lang) if source_lang in all_codes else 0
        self.source_lang_combo.setCurrentIndex(src_idx)
        col.addWidget(self.source_lang_combo)

        # DeepL grubu
        self.deepl_group = QGroupBox(tr('project_settings.group_deepl', 'DeepL API Key (Ücretli)'))
        deepl_lay = QFormLayout(self.deepl_group)
        deepl_lay.setSpacing(4)
        deepl_lay.setContentsMargins(8, 6, 8, 6)
        self.deepl_api_key_combo = QLineEdit()
        self.deepl_api_key_combo.setText(deepl_api)
        deepl_lay.addRow(QLabel(tr('project_settings.label_deepl_api_key', 'DeepL API Key:')))
        deepl_lay.addWidget(self.deepl_api_key_combo)
        col.addWidget(self.deepl_group)

        # Yandex grubu
        self.yandex_group = QGroupBox(tr('project_settings.group_yandex', 'Yandex API Key (Ücretsiz)'))
        yandex_lay = QFormLayout(self.yandex_group)
        yandex_lay.setSpacing(4)
        yandex_lay.setContentsMargins(8, 6, 8, 6)
        self.yandex_api_key_combo = QLineEdit()
        self.yandex_api_key_combo.setText(yandex_api)
        yandex_lay.addRow(QLabel(tr('project_settings.label_yandex_api_key', 'Yandex API Key:')))
        yandex_lay.addWidget(self.yandex_api_key_combo)
        col.addWidget(self.yandex_group)

        col.addStretch()
        return col


    # Kolon 2: API Key + MCP + Async/Batch + Terminoloji

    def _build_column2(self, api_key, mcp_endpoint_id,
                       async_enabled, async_threads,
                       batch_enabled, max_batch_chars, max_chapters_per_batch,
                       terminology_enabled):
        col = QVBoxLayout()
        col.setSpacing(8)
        col.addWidget(self._section_title('2. ' + tr('new_project.col2_title', 'Proje Ayarları')))

        # API Key seçimi
        col.addWidget(self._field_label(tr('project_settings.label_api_key_select', 'API Key Seç')))
        key_row = QHBoxLayout()
        self.api_key_combo = QComboBox()
        self.api_key_combo.currentIndexChanged.connect(self.on_api_combo_changed)
        key_row.addWidget(self.api_key_combo, 1)
        self.edit_keys_btn = QPushButton(tr('app_settings.btn_edit', 'Düzenle'))
        self.edit_keys_btn.setObjectName('smallBtn')
        self.edit_keys_btn.setFixedWidth(65)
        self.edit_keys_btn.clicked.connect(self.open_key_editor)
        key_row.addWidget(self.edit_keys_btn)
        col.addLayout(key_row)

        col.addWidget(self._field_label(tr('project_settings.label_current_api_key', 'Mevcut API Key')))
        self.api_key_input = QLineEdit()
        self.api_key_input.setText(api_key)
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        col.addWidget(self.api_key_input)

        # MCP grubu
        self.mcp_group = QGroupBox(tr('project_settings.group_mcp', 'Yapay Zeka Kaynağı (MCP)'))
        mcp_lay = QVBoxLayout(self.mcp_group)
        mcp_lay.setSpacing(5)
        mcp_lay.setContentsMargins(8, 6, 8, 6)
        self.use_custom_endpoint = QCheckBox(
            tr('project_settings.checkbox_custom_mcp', 'Bu proje için özel bağlantı kullan')
        )
        mcp_lay.addWidget(self.use_custom_endpoint)
        ep_row = QHBoxLayout()
        self.endpoint_combo = QComboBox()
        self.endpoint_combo.setEnabled(False)
        self._load_endpoints(mcp_endpoint_id)
        self.mcp_manage_btn = QPushButton(tr('project_settings.btn_mcp_manage', 'MCP Yönet'))
        self.mcp_manage_btn.setObjectName('smallBtn')
        self.mcp_manage_btn.setFixedWidth(90)
        self.mcp_manage_btn.clicked.connect(self.open_mcp_dialog)
        ep_row.addWidget(self.endpoint_combo, 1)
        ep_row.addWidget(self.mcp_manage_btn)
        mcp_lay.addLayout(ep_row)
        self.use_custom_endpoint.toggled.connect(self.endpoint_combo.setEnabled)
        if mcp_endpoint_id:
            self.use_custom_endpoint.setChecked(True)
        col.addWidget(self.mcp_group)

        # Özellikler grubu (Terminoloji Memory)
        self.features_group = QGroupBox(tr('project_settings.group_features', 'Otomatik Özellikler'))
        feat_lay = QVBoxLayout(self.features_group)
        feat_lay.setSpacing(4)
        feat_lay.setContentsMargins(8, 6, 8, 6)
        self.terminology_checkbox = QCheckBox(
            tr('project_settings.checkbox_terminology', 'Terminoloji Hafızası (Terminology Memory)')
        )
        self.terminology_checkbox.setChecked(terminology_enabled)
        self.terminology_checkbox.setToolTip(
            tr('project_settings.checkbox_terminology_tooltip',
               'Proje terminoloji sözlüğünü otomatik olarak prompta ekler.')
        )
        feat_lay.addWidget(self.terminology_checkbox)
        col.addWidget(self.features_group)

        # Performans grubu
        self.advanced_group = QGroupBox(tr('project_settings.group_advanced', 'Performans ve Altyapı'))
        adv_lay = QFormLayout()
        adv_lay.setSpacing(6)
        adv_lay.setContentsMargins(8, 6, 8, 6)
        self.advanced_layout = adv_lay

        self.async_checkbox = QCheckBox(
            tr('project_settings.checkbox_async', 'Asenkron Çeviri [RPM Değeri Önemli]')
        )
        self.async_checkbox.setChecked(async_enabled)
        self.async_threads_spinbox = QSpinBox()
        self.async_threads_spinbox.setMinimum(1)
        self.async_threads_spinbox.setMaximum(100)
        self.async_threads_spinbox.setValue(async_threads)
        self.async_threads_spinbox.setEnabled(async_enabled)
        self.async_checkbox.toggled.connect(self.async_threads_spinbox.setEnabled)

        self.batch_checkbox = QCheckBox(
            tr('project_settings.checkbox_batch', 'Toplu Çeviri / Batch Mode [TPM Değeri Önemli]')
        )
        self.batch_checkbox.setChecked(batch_enabled)
        self.batch_checkbox.toggled.connect(self._on_batch_toggled)

        self.batch_chars_spinbox = QSpinBox()
        self.batch_chars_spinbox.setMinimum(5000)
        self.batch_chars_spinbox.setMaximum(1000000)
        self.batch_chars_spinbox.setSingleStep(1000)
        self.batch_chars_spinbox.setValue(max_batch_chars)
        self.batch_chars_spinbox.setEnabled(batch_enabled)

        self.batch_chapters_spinbox = QSpinBox()
        self.batch_chapters_spinbox.setMinimum(1)
        self.batch_chapters_spinbox.setMaximum(100)
        self.batch_chapters_spinbox.setValue(max_chapters_per_batch)
        self.batch_chapters_spinbox.setEnabled(batch_enabled)

        adv_lay.addRow(self.async_checkbox)
        adv_lay.addRow(tr('project_settings.label_async_threads', 'Thread sayısı:'), self.async_threads_spinbox)
        adv_lay.addRow(self.batch_checkbox)
        adv_lay.addRow(tr('project_settings.label_max_chars_batch', 'Maks karakter/batch:'), self.batch_chars_spinbox)
        adv_lay.addRow(tr('project_settings.label_max_chapters_batch', 'Maks bölüm/batch:'), self.batch_chapters_spinbox)

        # Veritabanı taşıma butonu
        from core.database_manager import DatabaseManager
        project_path = get_project_dir(os.getcwd(), self.project_name)
        self.db_mgr = DatabaseManager(project_path)
        self.db_migrate_btn = QPushButton(
            tr('project_settings.btn_db_migrate', '📦 Eski Projeyi Veritabanına Taşı (Hızlandır)')
        )
        self.db_migrate_btn.setStyleSheet(
            'background-color: #0D47A1; color: white;'
            ' padding: 4px 10px; border-radius: 4px; font-size: 9pt;'
        )
        self.db_migrate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.db_migrate_btn.clicked.connect(self.run_db_migration)
        if self.db_mgr.db_exists():
            self.db_migrate_btn.setVisible(False)
        adv_lay.addRow(self.db_migrate_btn)

        self.advanced_group.setLayout(adv_lay)
        col.addWidget(self.advanced_group)
        col.addStretch()
        return col

    # Kolon 3: Prompt Seçimi + İçerik + Generator

    def _build_column3(self, start_promt):
        col = QVBoxLayout()
        col.setSpacing(8)
        col.addWidget(self._section_title('3. ' + tr('new_project.col3_title', 'Bağlantı & Gelişmiş')))

        col.addWidget(self._field_label(tr('project_settings.label_prompt_select', 'Prompt Seç')))
        promt_row = QHBoxLayout()
        self.promt_combo = QComboBox()
        self.promt_combo.currentIndexChanged.connect(self.on_promt_combo_changed)
        promt_row.addWidget(self.promt_combo, 1)
        self.edit_promt_btn = QPushButton(tr('app_settings.btn_edit', 'Düzenle'))
        self.edit_promt_btn.setObjectName('smallBtn')
        self.edit_promt_btn.setFixedWidth(65)
        self.edit_promt_btn.clicked.connect(self.open_promt_editor)
        promt_row.addWidget(self.edit_promt_btn)
        col.addLayout(promt_row)

        col.addWidget(self._field_label(tr('project_settings.label_prompt_content', 'Prompt İçeriği')))
        self.startpromtinput = QTextEdit()
        self.startpromtinput.setText(start_promt)
        self.startpromtinput.setMinimumHeight(110)
        self.startpromtinput.setMaximumHeight(220)
        col.addWidget(self.startpromtinput)

        # Prompt Generator butonu
        self.prompt_gen_btn = QPushButton(
            tr('project_settings.btn_prompt_gen', '⚡ Prompt Oluşturucu (Generator)')
        )
        self.prompt_gen_btn.setStyleSheet(
            'background-color: #880E4F; color: white; font-weight: bold;'
            ' padding: 6px 10px; border-radius: 4px; font-size: 9pt;'
        )
        self.prompt_gen_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.prompt_gen_btn.clicked.connect(self.open_prompt_generator)
        col.addWidget(self.prompt_gen_btn)

        col.addStretch()
        return col

    # Yardımcı widget oluşturucular
    def _section_title(self, text: str) -> QLabel:
        l = QLabel(text)
        l.setStyleSheet(f'color:{TEXT_MAIN}; font-size:13px; font-weight:700;')
        return l

    def _field_label(self, text: str) -> QLabel:
        l = QLabel(text)
        l.setStyleSheet(f'color:{TEXT_DIM}; font-size:11px;')
        return l

    def _vline(self) -> QFrame:
        v = QFrame()
        v.setFrameShape(QFrame.Shape.VLine)
        v.setStyleSheet(f'color: {BORDER};')
        return v

    # Provider görünürlük kontrolü
    def on_provider_changed(self):
        prov = self.provider_combo.currentData()
        is_llm    = (prov == 'llm')
        is_deepl  = (prov == 'deepl')
        is_yandex = (prov == 'yandex')

        self.deepl_group.setVisible(is_deepl)
        self.yandex_group.setVisible(is_yandex)
        self.mcp_group.setVisible(is_llm)
        self.api_key_input.setVisible(is_llm)
        self.api_key_combo.setEnabled(is_llm)
        self.edit_keys_btn.setEnabled(is_llm)
        self.promt_combo.setEnabled(is_llm)
        self.edit_promt_btn.setEnabled(is_llm)
        self.startpromtinput.setEnabled(is_llm)
        self.prompt_gen_btn.setEnabled(is_llm)
        self.features_group.setVisible(is_llm)
        self.advanced_group.setVisible(is_llm)

        self.batch_checkbox.setEnabled(is_llm)
        if not is_llm:
            self.batch_checkbox.setChecked(False)
        else:
            self.batch_checkbox.setToolTip('')

    def _on_batch_toggled(self, checked: bool):
        self.batch_chars_spinbox.setEnabled(checked)
        self.batch_chapters_spinbox.setEnabled(checked)

    # MCP / Key / Prompt yardımcıları
    def _load_endpoints(self, selected_id=None):
        self.endpoint_combo.clear()
        self.endpoint_combo.addItem(tr('new_project.combo_global_endpoint', 'Global Aktif Endpoint'), None)
        try:
            from core.llm_provider import load_endpoints
            data = load_endpoints()
            for ep in data.get('endpoints', []):
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
            QMessageBox.warning(
                self,
                tr('main_window.msg_structure_error_title', 'Hata'),
                tr('project_settings.prompt_gen_missing', 'Prompt Generator modülü henüz yüklenmemiş.')
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                tr('main_window.msg_structure_error_title', 'Hata'),
                f'Prompt Generator: {e}'
            )

    def refresh_combos(self):
        load_files_to_combo(self.api_key_combo, 'APIKeys')
        load_files_to_combo(self.promt_combo, 'Promts')

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

    # Veri Toplama
    def get_data(self):
        max_pages_text = self.maxPagesInput.text()
        max_pages = int(max_pages_text) if max_pages_text.isdigit() else None

        mcp_endpoint_id = None
        if self.use_custom_endpoint.isChecked():
            mcp_endpoint_id = self.endpoint_combo.currentData()

        api_key_name = self.api_key_combo.currentText()
        if api_key_name == tr('new_project.combo_select', 'Seçiniz...'):
            api_key_name = ''

        return {
            'link':                 self.projectLinkInput.text(),
            'max_pages':            max_pages,
            'max_retries':          self.maxRetriesInput.value(),
            'api_key':              self.api_key_input.text(),
            'deepl_api':            self.deepl_api_key_combo.text(),
            'yandex_api':           self.yandex_api_key_combo.text(),
            'api_key_name':         api_key_name,
            'Startpromt':           self.startpromtinput.toPlainText(),
            'mcp_endpoint_id':      mcp_endpoint_id,
            'terminology_enabled':  self.terminology_checkbox.isChecked(),
            'async_enabled':        self.async_checkbox.isChecked(),
            'async_threads':        self.async_threads_spinbox.value(),
            'batch_enabled':        self.batch_checkbox.isChecked(),
            'max_batch_chars':      self.batch_chars_spinbox.value(),
            'max_chapters_per_batch': self.batch_chapters_spinbox.value(),
            'translation_provider': self.provider_combo.currentData(),
            'source_lang':          self.source_lang_combo.currentData(),
        }

    # Veritabanı Taşıma
    def run_db_migration(self):
        from core.file_list_manager import FileListManager
        self.db_migrate_btn.setText(
            tr('project_settings.btn_db_migrate_running', 'Taşınıyor... Lütfen bekleyin')
        )
        self.db_migrate_btn.setEnabled(False)
        QApplication.processEvents()
        project_path = get_project_dir(os.getcwd(), self.project_name)
        try:
            legacy_flm = FileListManager(project_path)
            success = self.db_mgr.sync_directory_to_db(legacy_flm)
            if success:
                QMessageBox.information(
                    self,
                    tr('project_settings.msg_db_migrate_success_title', 'Başarılı'),
                    tr('project_settings.msg_db_migrate_success_body',
                       'Eski veriler başarıyla veritabanına taşındı!\nArtık dosya listeleri anında açılacak.')
                )
                self.db_migrate_btn.setVisible(False)
            else:
                QMessageBox.warning(
                    self,
                    tr('project_settings.msg_db_migrate_error_title', 'Hata'),
                    tr('project_settings.msg_db_migrate_error_body',
                       'Veritabanına taşıma işlemi sırasında bir hata oluştu.')
                )
                self.db_migrate_btn.setText(
                    tr('project_settings.btn_db_migrate', '📦 Eski Projeyi Veritabanına Taşı (Hızlandır)')
                )
                self.db_migrate_btn.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(
                self,
                tr('project_settings.msg_db_migrate_fail_title', 'Hata'),
                tr('project_settings.msg_db_migrate_fail_body',
                   'Beklenmeyen bir hata oluştu:\n{}').format(e)
            )
            self.db_migrate_btn.setText(
                tr('project_settings.btn_db_migrate', '📦 Eski Projeyi Veritabanına Taşı (Hızlandır)')
            )
            self.db_migrate_btn.setEnabled(True)
