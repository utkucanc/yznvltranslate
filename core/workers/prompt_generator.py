"""
Prompt Generator (PromtGen) — Proje bazlı, hikayenin ruhuna ve terimlerine
en uygun çeviri promptunu otomatik olarak üreten yapay zeka asistanı.

3 prompt üretir:
  - Prompt A (Literal): Birebir çeviri odaklı
  - Prompt B (Natural): Doğal ve akıcı çeviri odaklı
  - Prompt C (Balanced): Dengeli çeviri

PromptGeneratorDialog:  PyQt6 diyalog penceresi
"""
from core.localization import tr_log
import os
import random
import configparser
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel, QPushButton, QGroupBox, QRadioButton, QSpinBox, QMessageBox, QProgressBar, QTabWidget, QWidget, QFormLayout, QApplication, QSizePolicy
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject
from logger import app_logger
from core.localization import tr

class ContextBuilder:
    """Prompt üretimi için bağlam veri toplama."""

    def __init__(self, project_path: str, sample_count: int=2):
        self.project_path = project_path
        self.sample_count = sample_count

    def get_saved_prompts(self) -> str:
        """Kayıtlı başarılı promptları toplar."""
        prompts_folder = os.path.join(os.getcwd(), 'AppConfigs', 'Promts')
        prompts = []
        if os.path.exists(prompts_folder):
            for f in sorted(os.listdir(prompts_folder)):
                if f.endswith('.txt'):
                    try:
                        with open(os.path.join(prompts_folder, f), 'r', encoding='utf-8') as fh:
                            content = fh.read().strip()
                            if content:
                                prompts.append(f"--- {f.replace('.txt', '')} ---\n{content[:1000]}")
                    except Exception:
                        pass
        return '\n\n'.join(prompts[:3])

    def get_wiki_content(self, wiki_text: str='') -> str:
        """Wiki metni varsa döndürür."""
        return wiki_text.strip() if wiki_text else ''

    def get_sample_chapters(self, token_limit: int=None) -> tuple[str, int]:
        """2+2+2 metodu ile bölüm örnekleri toplar. Token limiti aşılırsa durur."""
        if token_limit is None:
            try:
                import json as _json
                _settings_file = os.path.join(os.getcwd(), 'AppConfigs', 'app_settings.json')
                if os.path.exists(_settings_file):
                    with open(_settings_file, 'r', encoding='utf-8') as _f:
                        _settings = _json.load(_f)
                    token_limit = _settings.get('promt_generator_max_tokens', 40000)
                else:
                    token_limit = 40000
            except Exception:
                token_limit = 40000
            app_logger.info(tr_log('core.workers.prompt_generator', 71, f'Prompt Gen token limiti ayarlardan okundu: {token_limit}'))
        try:
            from core.workers.token_counter import get_local_token_count_approx
        except ImportError:

            def get_local_token_count_approx(text):
                return int(len(text) / 2.5)
        dwnld_folder = os.path.join(self.project_path, 'dwnld')
        if not os.path.exists(dwnld_folder):
            return ('', 0)
        files = sorted([f for f in os.listdir(dwnld_folder) if f.endswith('.txt')])
        if not files:
            return ('', 0)
        n = self.sample_count
        total = len(files)
        selected = []
        selected.extend(files[:n])
        mid = total // 2
        mid_start = max(n, mid - n // 2)
        selected.extend(files[mid_start:mid_start + n])
        selected.extend(files[max(0, total - n):])
        seen = set()
        unique = []
        for f in selected:
            if f not in seen:
                seen.add(f)
                unique.append(f)
        samples = []
        acc_tokens = 0
        for f in unique:
            try:
                with open(os.path.join(dwnld_folder, f), 'r', encoding='utf-8') as fh:
                    content = fh.read()
                file_tokens = get_local_token_count_approx(content)
                if acc_tokens + file_tokens > token_limit and samples:
                    app_logger.info(tr_log('core.workers.prompt_generator', 112, f"Prompt örnekleme token limiti ({token_limit}) aşılacak, '{f}' atlandı."))
                    continue
                samples.append(f'--- {f} ---\n{content}')
                acc_tokens += file_tokens
            except Exception:
                pass
        return ('\n\n'.join(samples), acc_tokens)

    def build_context(self, wiki_text: str='') -> tuple[str, int]:
        """Tam bağlam metni oluşturur. (context, total_tokens) döndürür."""
        parts = []
        total_tokens = 0
        prompts = self.get_saved_prompts()
        if prompts:
            parts.append(f'## Kayıtlı Başarılı Çeviri Promptları:\n{prompts}')
        wiki = self.get_wiki_content(wiki_text)
        if wiki:
            parts.append(f'## Hikaye Wiki / Karakter ve Evren Bilgileri:\n{wiki}')
        (samples, sample_tokens) = self.get_sample_chapters()
        total_tokens += sample_tokens
        if samples:
            parts.append(f'## Hikaye Bölüm Örnekleri (Orijinal Dil):\n{samples}')
        return ('\n\n'.join(parts), total_tokens)

def _get_meta_prompt_template() -> str:
    """
    app_settings.json'daki prompt_gen_prompt_override boş değilse onu döndürür,
    boşsa locale'den gelen META_PROMPT_TEMPLATE varsayılanını kullanır.
    """
    try:
        import json as _json
        _settings_file = os.path.join(os.getcwd(), 'AppConfigs', 'app_settings.json')
        if os.path.exists(_settings_file):
            with open(_settings_file, 'r', encoding='utf-8') as _f:
                _data = _json.load(_f)
            override = _data.get('prompt_gen_prompt_override', '').strip()
            if override:
                return override
    except Exception:
        pass
    return tr('promt_generator.promt', 'deneme')
META_PROMPT_TEMPLATE = tr('promt_generator.promt', 'deneme')

class PromptGenWorker(QObject):
    """Arka planda prompt üretim işlemi."""
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, context: str, model_version: str='gemini-2.5-flash', api_key: str=None, endpoint_id: str=None):
        super().__init__()
        self.context = context
        self.model_version = model_version
        self.api_key = api_key
        self.endpoint_id = endpoint_id

    def run(self):
        try:
            self.progress.emit(tr('prompt_generator_dialog.progress_initializing', 'LLM sağlayıcı başlatılıyor...'))
            app_logger.info(tr_log('core.workers.prompt_generator', 183, 'LLM sağlayıcı başlatılıyor...'))
            from core.llm_provider import LLMProvider
            provider = None
            if self.endpoint_id:
                provider = LLMProvider(endpoint_id=self.endpoint_id)
            elif self.api_key:
                provider = LLMProvider(endpoint={'id': 'project_gemini', 'name': 'Proje Gemini', 'type': 'gemini', 'model_id': self.model_version, 'base_url': None, 'use_key_rotation': False, 'headers': {}}, api_key=self.api_key)
            if provider is None:
                provider = LLMProvider()
            info = provider.get_info()
            self.progress.emit(tr('prompt_generator_dialog.progress_generating', 'Prompt üretiliyor ({name} — {model_id})... Bu işlem 30-60 saniye sürebilir').format(name=info['name'], model_id=info['model_id']))
            app_logger.warning(tr_log('core.workers.prompt_generator', 210, f"Debug - Model: {info['name']} ({info['model_id']}) "))
            app_logger.info(tr_log('core.workers.prompt_generator', 211, f"Prompt üretiliyor ({info['name']} — {info['model_id']})... Bu işlem 30-60 saniye sürebilir"))
            full_prompt = _get_meta_prompt_template().format(context=self.context)
            result = provider.generate(full_prompt)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(tr('prompt_generator_dialog.error_generation', 'Prompt üretim hatası: {error}').format(error=str(e)))

def parse_generated_prompts(raw_text: str) -> dict:
    """LLM yanıtından 3 promptu ayrıştırır."""
    prompts = {'A': '', 'B': '', 'C': ''}
    try:
        if '===PROMPT_A===' in raw_text:
            parts = raw_text.split('===PROMPT_A===')
            if len(parts) > 1:
                rest = parts[1]
                if '===PROMPT_B===' in rest:
                    (a_part, rest) = rest.split('===PROMPT_B===', 1)
                    prompts['A'] = a_part.strip()
                    if '===PROMPT_C===' in rest:
                        (b_part, rest) = rest.split('===PROMPT_C===', 1)
                        prompts['B'] = b_part.strip()
                        if '===END===' in rest:
                            c_part = rest.split('===END===')[0]
                        else:
                            c_part = rest
                        prompts['C'] = c_part.strip()
    except Exception as e:
        app_logger.error(tr_log('core.workers.prompt_generator', 243, f'Prompt ayrıştırma hatası: {e}'))
        app_logger.error(tr_log('core.workers.prompt_generator', 244, f'Ayrıştırma hatası: {str(e)}'))
    if not any(prompts.values()):
        prompts['A'] = raw_text.strip()
        QMessageBox.information(None, tr('prompt_generator_dialog.msg_parse_fail_title', 'Ayırma Başarısız!'), tr('prompt_generator_dialog.msg_parse_fail_body', 'Prompt ayrıştırma başarısız, ham metin A promptuna kaydedildi.'))
        app_logger.error(tr_log('core.workers.prompt_generator', 250, f'Ayrıştırma başarısız, ham metin A promptuna kaydedildi.'))
    return prompts

class PromptGeneratorDialog(QDialog):
    """Prompt Generator UI penceresi."""

    def __init__(self, project_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr('prompt_generator_dialog.window_title', 'Prompt Generator — {project_name}').format(project_name=project_name))
        self.resize(800, 700)
        self.project_name = project_name
        self.project_path = os.path.join(os.getcwd(), project_name)
        self.generated_prompts = {'A': '', 'B': '', 'C': ''}
        self.selected_prompt = ''
        self._thread = None
        self._worker = None
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        wiki_group = QGroupBox()
        wiki_group.setTitle('')
        wiki_layout = QVBoxLayout()
        wiki_layout.setSpacing(5)
        wiki_layout.setContentsMargins(8, 8, 8, 8)
        wiki_title = QLabel(f"{tr('prompt_generator_dialog.wiki_title', '📚  Wiki / Karakter Bilgileri')} <span style='color:#F9E2AF; font-size:9pt;'>{tr('prompt_generator_dialog.wiki_title_optional', '(OPSİYONEL — Boş bırakılabilir)')}</span>")
        wiki_title.setFont(QFont('Segoe UI', 11, QFont.Weight.Bold))
        wiki_title.setTextFormat(Qt.TextFormat.RichText)
        wiki_title.setStyleSheet('color: #89B4FA; margin-bottom: 4px;')
        wiki_layout.addWidget(wiki_title)
        self.wiki_edit = QTextEdit()
        self.wiki_edit.setPlaceholderText(tr('prompt_generator_dialog.wiki_placeholder', ''))
        self.wiki_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.wiki_edit.setMinimumHeight(140)
        self.wiki_edit.setMaximumHeight(220)
        wiki_layout.addWidget(self.wiki_edit)
        wiki_group.setLayout(wiki_layout)
        layout.addWidget(wiki_group)
        sample_layout = QHBoxLayout()
        sample_layout.addWidget(QLabel(tr('prompt_generator_dialog.label_sample_count', 'Bölüm örnekleme sayısı (baştan/ortadan/sondan):')))
        self.sample_spin = QSpinBox()
        self.sample_spin.setMinimum(1)
        self.sample_spin.setMaximum(5)
        self.sample_spin.setValue(2)
        sample_layout.addWidget(self.sample_spin)
        sample_layout.addStretch()
        layout.addLayout(sample_layout)
        self.generate_btn = QPushButton(tr('prompt_generator_dialog.btn_generate', '🚀 Prompt Üret (3 Varyant)'))
        self.generate_btn.setStyleSheet('background-color: #E91E63; color: white; font-weight: bold; padding: 12px; border-radius: 6px; font-size: 13pt;')
        self.generate_btn.clicked.connect(self.start_generation)
        layout.addWidget(self.generate_btn)
        self.progress_label = QLabel('')
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.progress_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        self.tabs = QTabWidget()
        self.tabs.setVisible(False)
        self.prompt_edits = {}
        self.radio_buttons = {}
        labels = {
            'A': tr('prompt_generator_dialog.tab_label_a', '📖 Prompt A — Literal (Birebir)'),
            'B': tr('prompt_generator_dialog.tab_label_b', '💬 Prompt B — Natural (Doğal)'),
            'C': tr('prompt_generator_dialog.tab_label_c', '⚖️ Prompt C — Balanced (Dengeli)'),
        }
        for (key, label) in labels.items():
            tab = QWidget()
            tab_layout = QVBoxLayout(tab)
            radio = QRadioButton(tr('prompt_generator_dialog.radio_use_prompt', 'Bu promptu kullan ({key})').format(key=key))
            radio.setFont(QFont('Arial', 10, QFont.Weight.Bold))
            self.radio_buttons[key] = radio
            tab_layout.addWidget(radio)
            edit = QTextEdit()
            edit.setPlaceholderText(tr('prompt_generator_dialog.placeholder_prompt_not_generated', 'Prompt henüz üretilmedi...'))
            self.prompt_edits[key] = edit
            tab_layout.addWidget(edit)
            self.tabs.addTab(tab, label)
        self.radio_buttons['C'].setChecked(True)
        layout.addWidget(self.tabs)
        bottom_layout = QHBoxLayout()
        self.save_btn = QPushButton(tr('prompt_generator_dialog.btn_save_and_use', '💾 Seçileni Kaydet ve Kullan'))
        self.save_btn.setStyleSheet('background-color: #4CAF50; color: white; font-weight: bold; padding: 10px; border-radius: 5px;')
        self.save_btn.setVisible(False)
        self.save_btn.clicked.connect(self.save_and_use)
        bottom_layout.addWidget(self.save_btn)
        layout.addLayout(bottom_layout)

    def start_generation(self):
        """Prompt üretimini başlatır."""
        self.generate_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_label.setText(tr('prompt_generator_dialog.progress_building_context', 'Bağlam derleniyor...'))
        app_logger.info(tr_log('core.workers.prompt_generator', 381, 'Bağlam derleniyor...'))
        QApplication.processEvents()
        builder = ContextBuilder(self.project_path, self.sample_spin.value())
        (context, total_tokens) = builder.build_context(self.wiki_edit.toPlainText())
        if not context.strip():
            QMessageBox.warning(self, tr('prompt_generator_dialog.msg_no_context_title', 'Uyarı'), tr('prompt_generator_dialog.msg_no_context_body', 'Bağlam oluşturulamadı. Lütfen wiki bilgisi girin veya proje dosyalarını kontrol edin.'))
            app_logger.error(tr_log('core.workers.prompt_generator', 390, 'Bağlam oluşturulamadı. Lütfen wiki bilgisi girin veya proje dosyalarını kontrol edin.'))
            self.generate_btn.setEnabled(True)
            self.progress_bar.setVisible(False)
            self.progress_label.clear()
            return
        self.progress_label.setText(tr('prompt_generator_dialog.progress_sample_ready', '📊 Örneklem hazırlandı: ~{total_tokens} token. LLM bağlantısı kuruluyor...').format(total_tokens=f'{total_tokens:,}'))
        app_logger.info(tr_log('core.workers.prompt_generator', 398, f'📊 Örneklem hazırlandı: ~{total_tokens:,} token. LLM bağlantısı kuruluyor...'))
        import configparser
        model_version = 'gemini-2.5-flash'
        gversion_path = os.path.join(os.getcwd(), 'AppConfigs', 'GVersion.ini')
        if os.path.exists(gversion_path):
            try:
                gconfig = configparser.ConfigParser()
                gconfig.read(gversion_path)
                model_version = gconfig.get('Version', 'model_name', fallback=model_version)
            except Exception:
                pass
        config = configparser.ConfigParser()
        config_path = os.path.join(self.project_path, 'config', 'config.ini')
        api_key = None
        endpoint_id = None
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config.read_file(f)
                api_key = config.get('API', 'gemini_api_key', fallback=None)
                endpoint_id = config.get('MCP', 'endpoint_id', fallback=None)
            except Exception:
                pass
        self._thread = QThread()
        self._worker = PromptGenWorker(context, model_version=model_version, api_key=api_key, endpoint_id=endpoint_id)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self.on_generation_finished)
        self._worker.error.connect(self.on_generation_error)
        self._worker.progress.connect(self.on_progress)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.start()

    def on_progress(self, msg):
        self.progress_label.setText(msg)

    def on_generation_finished(self, raw_result):
        self.progress_bar.setVisible(False)
        self.progress_label.setText(tr('prompt_generator_dialog.progress_done', 'Prompt üretimi tamamlandı!'))
        app_logger.info(tr_log('core.workers.prompt_generator', 446, 'Prompt üretimi tamamlandı!'))
        self.generate_btn.setEnabled(True)
        self.generated_prompts = parse_generated_prompts(raw_result)
        for key in ['A', 'B', 'C']:
            self.prompt_edits[key].setText(self.generated_prompts[key])
        self.tabs.setVisible(True)
        self.save_btn.setVisible(True)
        self._cleanup_thread()

    def on_generation_error(self, msg):
        self.progress_bar.setVisible(False)
        self.progress_label.setText(tr('prompt_generator_dialog.progress_error', 'Hata: {msg}').format(msg=msg))
        self.generate_btn.setEnabled(True)
        QMessageBox.critical(self, tr('prompt_generator_dialog.msg_error_title', 'Prompt Üretim Hatası'), msg)
        app_logger.error(tr_log('core.workers.prompt_generator', 463, f'Prompt Üretim Hatası: {str(msg)}'))
        self._cleanup_thread()

    def _cleanup_thread(self):
        """Thread ve worker'ı güvenli şekilde temizler."""
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(5000)
        self._worker = None
        self._thread = None

    def closeEvent(self, event):
        """Dialog kapatılırken çalışan thread varsa bekle."""
        if self._thread is not None and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(5000)
        self._worker = None
        self._thread = None
        event.accept()

    def save_and_use(self):
        """Seçili promptu kaydeder ve diyaloğu kapatır."""
        selected_key = None
        for (key, radio) in self.radio_buttons.items():
            if radio.isChecked():
                selected_key = key
                break
        if not selected_key:
            QMessageBox.warning(self, tr('prompt_generator_dialog.msg_no_selection_title', 'Seçim Yok'), tr('prompt_generator_dialog.msg_no_selection_body', 'Lütfen bir prompt seçin.'))
            return
        prompt_text = self.prompt_edits[selected_key].toPlainText().strip()
        if not prompt_text:
            QMessageBox.warning(self, tr('prompt_generator_dialog.msg_empty_prompt_title', 'Boş Prompt'), tr('prompt_generator_dialog.msg_empty_prompt_body', 'Seçili prompt boş. Lütfen önce prompt üretin.'))
            return
        self.selected_prompt = prompt_text
        try:
            prompts_folder = os.path.join(os.getcwd(), 'AppConfigs', 'Promts')
            os.makedirs(prompts_folder, exist_ok=True)
            label_map = {'A': 'Literal', 'B': 'Natural', 'C': 'Balanced'}
            for key in ['A', 'B', 'C']:
                content = self.prompt_edits[key].toPlainText().strip()
                if content:
                    filename = f'{self.project_name}_Prompt_{key}.txt'
                    filepath = os.path.join(prompts_folder, filename)
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(content)
            QMessageBox.information(self, tr('prompt_generator_dialog.msg_save_success_title', 'Başarılı'), tr('prompt_generator_dialog.msg_save_success_body', '3 prompt kaydedildi.\nSeçilen: Prompt {key} ({label})').format(key=selected_key, label=label_map[selected_key]))
        except Exception as e:
            QMessageBox.warning(self, tr('prompt_generator_dialog.msg_save_warn_title', 'Kayıt Uyarı'), tr('prompt_generator_dialog.msg_save_warn_body', 'Prompt kullanılacak ancak dosyaya kaydedilemedi: {error}').format(error=e))
        # Projenin config.ini'sine de yaz
        try:
            config_path = os.path.join(self.project_path, 'config', 'config.ini')
            cfg = configparser.ConfigParser()
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    cfg.read_file(f)
            if not cfg.has_section('Startpromt'):
                cfg.add_section('Startpromt')
            cfg['Startpromt']['startpromt'] = prompt_text
            with open(config_path, 'w', encoding='utf-8') as f:
                cfg.write(f)
            app_logger.info(tr_log('core.workers.prompt_generator', 408, f'Prompt proje config.ini\'ye kaydedildi: {config_path}'))
        except Exception as e:
            app_logger.warning(tr_log('core.workers.prompt_generator', 410, f'Prompt config.ini\'ye kaydedilemedi: {e}'))
        self.accept()

    def get_selected_prompt(self) -> str:
        """Seçilen prompt metnini döndürür."""
        return self.selected_prompt