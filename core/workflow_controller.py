"""
WorkflowController — Zincirleme İşlem Orkestra Şefi.

State Machine mantığıyla sıralı işlem yürütür:
  IDLE → DOWNLOADING → SPLITTING → GENERATING_PROMPT → EXTRACTING_TERMINOLOGY → TRANSLATING → COMPLETED

Her aşama sessiz (headless) çalışır — QMessageBox göstermez.
Aşama bitişlerinde log kaydı alarak sonraki aşamaya otomatik geçer.
"""

import os
import configparser
from enum import Enum
from PyQt6.QtCore import QThread, QTimer
from PyQt6.QtWidgets import QMessageBox, QDialog
from logger import app_logger


class WorkflowState(Enum):
    IDLE = "idle"
    DOWNLOADING = "downloading"
    SPLITTING = "splitting"
    GENERATING_PROMPT = "generating_prompt"
    EXTRACTING_TERMINOLOGY = "extracting_terminology"
    TRANSLATING = "translating"
    COMPLETED = "completed"
    ERROR = "error"


class WorkflowController:
    """Zincirleme işlem orkestra şefi — 5 aşamalı otomatik pipeline."""

    def __init__(self, main_window):
        self.win = main_window
        self.state = WorkflowState.IDLE
        self.config = {}  # Dialog'dan gelen workflow ayarları
        self._thread = None
        self._worker = None
        self._stages = []  # Çalıştırılacak aşamalar (sıralı)
        self._current_stage_index = -1
        self._downloaded_file_path = None  # İndirilen dosya yolu (split için)

    # Başlatma 

    def start(self):
        """Workflow'u başlatır — Dialog açar, onay alır, pipeline başlatır."""
        if self.state != WorkflowState.IDLE:
            QMessageBox.warning(self.win, "Çalışıyor", "Bir workflow zaten devam ediyor.")
            return

        # Proje kontrolü
        current_item = self.win.project_list.currentItem()
        if not current_item:
            QMessageBox.warning(self.win, "Proje Seçilmedi", "Lütfen sol listeden bir proje seçin.")
            return

        project_name = current_item.text()
        project_path = os.path.join(os.getcwd(), project_name)
        config_path = os.path.join(project_path, "config", "config.ini")
        if not os.path.exists(config_path):
            QMessageBox.critical(self.win, "Hata",
                                 f"'{project_name}' projesi için config.ini bulunamadı.")
            return

        # Dialog aç
        from ui.automation_setup_dialog import AutomationSetupDialog
        dialog = AutomationSetupDialog(project_name, project_path, parent=self.win)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.config = dialog.get_config()
        app_logger.info(f"Workflow başlatılıyor: {project_name}")
        app_logger.info(f"Workflow ayarları: {self.config}")

        # Çalıştırılacak aşamaları belirle
        self._stages = []
        if self.config.get("download_enabled"):
            self._stages.append("download")
            self._stages.append("split")  # İndirme sonrası otomatik bölme
        if self.config.get("prompt_enabled"):
            self._stages.append("prompt")
        if self.config.get("terminology_enabled"):
            self._stages.append("terminology")
        if self.config.get("translation_enabled"):
            self._stages.append("translation")

        if not self._stages:
            return

        # UI kilitle
        self._lock_ui()
        self._current_stage_index = -1
        self._advance_to_next_stage()

    # Aşama Yönetimi 

    def _advance_to_next_stage(self):
        """Sıradaki aşamaya geçer."""
        self._current_stage_index += 1

        if self._current_stage_index >= len(self._stages):
            self._on_workflow_completed()
            return

        stage = self._stages[self._current_stage_index]
        stage_num = self._current_stage_index + 1
        total_stages = len(self._stages)

        app_logger.info(f"Workflow aşama {stage_num}/{total_stages}: {stage}")
        self.win.statusLabel.setText(
            f"Durum: 🚀 Workflow [{stage_num}/{total_stages}] — {self._stage_display_name(stage)}"
        )

        if stage == "download":
            self.state = WorkflowState.DOWNLOADING
            self._start_download()
        elif stage == "split":
            self.state = WorkflowState.SPLITTING
            self._start_splitting()
        elif stage == "prompt":
            self.state = WorkflowState.GENERATING_PROMPT
            self._start_prompt_generation()
        elif stage == "terminology":
            self.state = WorkflowState.EXTRACTING_TERMINOLOGY
            self._start_terminology_extraction()
        elif stage == "translation":
            self.state = WorkflowState.TRANSLATING
            self._start_translation()

    @staticmethod
    def _stage_display_name(stage: str) -> str:
        names = {
            "download": "İndirme",
            "split": "Bölümlere Ayırma",
            "prompt": "Prompt Üretme",
            "terminology": "Terminoloji Çıkarma",
            "translation": "Çeviri",
        }
        return names.get(stage, stage)

    # Aşama 1: İndirme

    def _start_download(self):
        """Selenium ile indirme — Cloudflare kontrollü."""
        project_path = self.config["project_path"]
        download_folder = os.path.join(project_path, "dwnld")
        os.makedirs(download_folder, exist_ok=True)

        # Proje linkini oku
        cfg = configparser.ConfigParser()
        config_path = os.path.join(project_path, "config", "config.ini")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg.read_file(f)
            project_link = cfg.get("ProjectInfo", "link", fallback=None)
        except Exception:
            project_link = None

        if not project_link:
            app_logger.error("Workflow İndirme: Proje linki bulunamadı.")
            self._on_stage_error("Proje linki config.ini'de bulunamadı.")
            return

        from core.workers.workflow_worker import WorkflowDownloadWorker

        self._thread = QThread()
        self._worker = WorkflowDownloadWorker(
            base_url=project_link,
            download_folder=download_folder,
            site=self.config.get("download_site", "69shuba"),
            chapter_limit=self.config.get("download_chapter_limit")
        )
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._on_download_finished)
        self._worker.error.connect(self._on_stage_error)
        self._worker.progress.connect(self._on_progress)
        self._worker.status_message.connect(
            lambda msg: self.win.statusLabel.setText(f"Durum: 🚀 İndirme — {msg}")
        )
        self._worker.file_downloaded.connect(self._on_file_downloaded)
        self._worker.cloudflare_detected.connect(self._on_cloudflare_detected)

        self.win.progressBar.setValue(0)
        self.win.progressBar.setMaximum(100)
        self.win.progressBar.setVisible(True)

        self._thread.start()

    def _on_cloudflare_detected(self):
        """Cloudflare algılandığında kullanıcıya onay penceresi açar."""
        from ui.selenium_menu_dialog import SeleniumMenuDialog
        # Basit bir onay diyaloğu
        reply = QMessageBox.information(
            self.win, "Cloudflare Algılandı",
            "Cloudflare bot koruması algılandı.\n"
            "Lütfen açılan tarayıcıda bot kontrolünü aşın ve\n"
            "kitabın 1. bölümüne gidin.\n\n"
            "Hazır olduğunuzda 'Tamam' butonuna basın.",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Ok
        )
        if reply == QMessageBox.StandardButton.Ok:
            if self._worker:
                self._worker.user_confirmed = True
                self._worker.selenium_command = self.config.get("download_site", "booktoki")
        else:
            if self._worker:
                self._worker.selenium_command = "cancel"
                self._worker.is_running = False

    def _on_file_downloaded(self, file_path, filename):
        """Dosya indirildiğinde yolu sakla, log kaydet ve DB senkronize et."""
        self._downloaded_file_path = file_path
        app_logger.info(f"Workflow İndirme: Dosya indirildi — {filename}")
        self.win.sync_database_if_exists()
        self.win.update_file_list_from_selection()

    def _on_download_finished(self):
        """İndirme aşaması tamamlandığında sessizce sonraki aşamaya geç."""
        app_logger.info("Workflow İndirme: Aşama tamamlandı.")
        self._cleanup_thread()
        self.win.sync_database_if_exists()
        self.win.update_file_list_from_selection()
        # Sessizce sonraki aşamaya geç
        QTimer.singleShot(500, self._advance_to_next_stage)

    # Aşama 1.5: Bölme 

    def _start_splitting(self):
        """İndirilen toplu dosyayı bölümlere ayırır — SplitWorker kullanılır."""
        project_path = self.config["project_path"]
        download_folder = os.path.join(project_path, "dwnld")

        # İndirilen dosyayı bul
        input_file = self._downloaded_file_path
        if not input_file or not os.path.exists(input_file):
            # dwnld klasöründeki en yeni .txt dosyasını bul
            try:
                txt_files = [
                    os.path.join(download_folder, f)
                    for f in os.listdir(download_folder)
                    if f.endswith(".txt")
                ]
                if txt_files:
                    input_file = max(txt_files, key=os.path.getmtime)
                else:
                    app_logger.warning("Workflow Bölme: Bölünecek dosya bulunamadı, aşama atlanıyor.")
                    self._advance_to_next_stage()
                    return
            except Exception as e:
                app_logger.error(f"Workflow Bölme: Dosya arama hatası: {e}")
                self._advance_to_next_stage()
                return

        app_logger.info(f"Workflow Bölme: Dosya bölünüyor — {input_file}")
        self.win.statusLabel.setText("Durum: 🚀 Bölme — Bölümlere ayrılıyor...")

        from core.workers.split_worker import SplitWorker

        self._thread = QThread()
        self._worker = SplitWorker(
            input_file_path=input_file,
            output_folder=download_folder
        )
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._on_splitting_finished)
        self._worker.error.connect(self._on_split_error)
        self._worker.progress.connect(self._on_progress)
        self._worker.file_created.connect(
            lambda name: self.win.statusLabel.setText(f"Durum: 🚀 Bölme — {name}")
        )

        self.win.progressBar.setValue(0)
        self.win.progressBar.setMaximum(0)  # Belirsiz progress
        self.win.progressBar.setVisible(True)

        self._thread.start()

    def _on_split_error(self, message: str):
        """Bölme hatası — dosyada uygun başlık yoksa atla, diğer hatalarda durdur."""
        if "başlığı bulunamadı" in message:
            app_logger.warning(f"Workflow Bölme: {message} — Dosya zaten bölümlenmiş olabilir, atlanıyor.")
            self._cleanup_thread()
            QTimer.singleShot(300, self._advance_to_next_stage)
        else:
            self._on_stage_error(message)

    def _on_splitting_finished(self):
        """Bölme tamamlandığında dosya listesini güncelle ve devam et."""
        app_logger.info("Workflow Bölme: Aşama tamamlandı.")
        self._cleanup_thread()
        self.win.sync_database_if_exists()
        self.win.update_file_list_from_selection()
        QTimer.singleShot(300, self._advance_to_next_stage)

    # Aşama 2: Prompt Üretme

    def _start_prompt_generation(self):
        """Prompt üretme — mevcut PromptGenWorker kullanılır, sessiz bitiş."""
        project_path = self.config["project_path"]
        project_name = self.config["project_name"]

        from core.workers.prompt_generator import ContextBuilder, PromptGenWorker

        self.win.statusLabel.setText("Durum: 🚀 Prompt — Bağlam derleniyor...")
        self.win.progressBar.setMaximum(0)  # Belirsiz progress

        # Bağlam oluştur
        builder = ContextBuilder(project_path, sample_count=2)
        context, total_tokens = builder.build_context()

        if not context.strip():
            app_logger.warning("Workflow Prompt: Bağlam oluşturulamadı, aşama atlanıyor.")
            self._advance_to_next_stage()
            return

        app_logger.info(f"Workflow Prompt: Bağlam hazır, ~{total_tokens} token.")

        # API/MCP yapılandırması
        api_key, endpoint_id, model_version = self._resolve_api_config(
            self.config.get("prompt_api", {})
        )

        self._thread = QThread()
        self._worker = PromptGenWorker(
            context,
            model_version=model_version,
            api_key=api_key,
            endpoint_id=endpoint_id
        )
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._on_prompt_finished)
        self._worker.error.connect(self._on_stage_error)
        self._worker.progress.connect(
            lambda msg: self.win.statusLabel.setText(f"Durum: 🚀 Prompt — {msg}")
        )

        self._thread.start()

    def _on_prompt_finished(self, raw_result: str):
        """Prompt üretimi tamamlandığında seçilen promptu kaydet."""
        app_logger.info("Workflow Prompt: Üretim tamamlandı.")

        from core.workers.prompt_generator import parse_generated_prompts

        prompts = parse_generated_prompts(raw_result)
        prompt_type = self.config.get("prompt_type", "C")
        selected_prompt = prompts.get(prompt_type, "")

        if not selected_prompt:
            # Herhangi birini al
            for key in ["C", "B", "A"]:
                if prompts.get(key):
                    selected_prompt = prompts[key]
                    prompt_type = key
                    break

        if selected_prompt:
            # Promptları dosyaya kaydet
            project_name = self.config["project_name"]
            prompts_folder = os.path.join(os.getcwd(), "AppConfigs", "Promts")
            os.makedirs(prompts_folder, exist_ok=True)

            for key in ["A", "B", "C"]:
                content = prompts.get(key, "")
                if content:
                    filename = f"{project_name}_Prompt_{key}.txt"
                    filepath = os.path.join(prompts_folder, filename)
                    try:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(content)
                    except Exception as e:
                        app_logger.warning(f"Prompt dosyası kaydedilemedi: {e}")

            # Seçilen promptu config.ini'ye yaz
            project_path = self.config["project_path"]
            config_path = os.path.join(project_path, "config", "config.ini")
            cfg = configparser.ConfigParser()
            try:
                if os.path.exists(config_path):
                    with open(config_path, "r", encoding="utf-8") as f:
                        cfg.read_file(f)
                if "Startpromt" not in cfg:
                    cfg["Startpromt"] = {}
                cfg["Startpromt"]["startpromt"] = selected_prompt
                with open(config_path, "w", encoding="utf-8") as f:
                    cfg.write(f)
                app_logger.info(f"Workflow Prompt: Prompt {prompt_type} config.ini'ye kaydedildi.")
            except Exception as e:
                app_logger.error(f"Workflow Prompt: Config yazma hatası: {e}")

        self._cleanup_thread()
        QTimer.singleShot(300, self._advance_to_next_stage)

    # Aşama 3: Terminoloji

    def _start_terminology_extraction(self):
        """Terminoloji çıkarma — MLTerminologyWorker kullanılır, sessiz bitiş."""
        project_path = self.config["project_path"]
        end_chapter = self.config.get("terminology_end_chapter", None)

        from core.workers.ml_terminology_worker import MLTerminologyWorker

        self.win.statusLabel.setText("Durum: 🚀 Terminoloji — Çıkarma başlıyor...")
        self.win.progressBar.setMaximum(0)

        # Başlangıç bölümü: son işlemin bitişinden devam et
        start_ch = 1
        try:
            cfg = configparser.ConfigParser()
            config_path = os.path.join(project_path, "config", "config.ini")
            if os.path.exists(config_path):
                cfg.read(config_path, encoding="utf-8")
                last_end = cfg.getint("TerminologyOp", "last_end_chapter", fallback=0)
                if last_end > 0:
                    start_ch = last_end + 1
        except Exception:
            pass

        self._worker = MLTerminologyWorker(
            project_path,
            start_chapter=start_ch,
            end_chapter=end_chapter
        )
        self._worker.progress_update.connect(
            lambda msg: self.win.statusLabel.setText(f"Durum: 🚀 Terminoloji — {msg}")
        )
        self._worker.error_signal.connect(self._on_stage_error)
        self._worker.finished_signal.connect(
            lambda actual_end: self._on_terminology_finished(project_path, start_ch, actual_end)
        )

        # MLTerminologyWorker QThread bazlı — doğrudan start()
        self._worker.start()

    def _on_terminology_finished(self, project_path: str, start_ch: int, actual_end_ch: int):
        """Terminoloji çıkarma tamamlandığında config güncelle ve devam et."""
        app_logger.info(
            f"Workflow Terminoloji: Tamamlandı. Bölümler: {start_ch} → {actual_end_ch}"
        )

        # Config.ini'ye son işlem bilgisini yaz
        config_path = os.path.join(project_path, "config", "config.ini")
        cfg = configparser.ConfigParser()
        try:
            if os.path.exists(config_path):
                cfg.read(config_path, encoding="utf-8")
            if "TerminologyOp" not in cfg:
                cfg["TerminologyOp"] = {}
            cfg["TerminologyOp"]["last_start_chapter"] = str(start_ch)
            cfg["TerminologyOp"]["last_end_chapter"] = str(actual_end_ch)
            with open(config_path, "w", encoding="utf-8") as f:
                cfg.write(f)
        except Exception as e:
            app_logger.warning(f"Terminoloji bölüm bilgisi yazılamadı: {e}")

        self._worker = None
        QTimer.singleShot(300, self._advance_to_next_stage)

    # Aşama 4: Çeviri

    def _start_translation(self):
        """Çeviri aşaması — config.ini güncelleyip mevcut TranslationController'ı kullanır."""
        project_path = self.config["project_path"]
        config_path = os.path.join(project_path, "config", "config.ini")

        # Workflow ayarlarını config.ini'ye yaz
        cfg = configparser.ConfigParser()
        try:
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg.read_file(f)

            # API / MCP — dialog'dan seçilen endpoint'i yaz
            trans_api = self.config.get("translation_api", {})
            api_type = trans_api.get("type", "")

            if api_type in ("mcp", "project_mcp"):
                # MCP endpoint seçildi
                if "MCP" not in cfg:
                    cfg["MCP"] = {}
                cfg["MCP"]["endpoint_id"] = trans_api.get("id", "")
                app_logger.info(f"Workflow Çeviri: MCP endpoint ayarlandı → {trans_api.get('id')}")
            elif api_type == "project_api":
                # Doğrudan API anahtarı seçildi
                if "API" not in cfg:
                    cfg["API"] = {}
                cfg["API"]["gemini_api_key"] = trans_api.get("key", "")
                app_logger.info("Workflow Çeviri: API anahtarı ayarlandı.")

            # Features
            if "Features" not in cfg:
                cfg["Features"] = {}
            cfg["Features"]["async_enabled"] = str(self.config.get("async_enabled", False))
            cfg["Features"]["async_threads"] = str(self.config.get("async_threads", 3))

            # Batch
            if "Batch" not in cfg:
                cfg["Batch"] = {}
            cfg["Batch"]["batch_enabled"] = str(self.config.get("batch_enabled", False))
            cfg["Batch"]["max_batch_chars"] = str(self.config.get("batch_max_chars", 33000))

            with open(config_path, "w", encoding="utf-8") as f:
                cfg.write(f)

            app_logger.info("Workflow Çeviri: Config.ini güncellendi.")
        except Exception as e:
            app_logger.error(f"Workflow Çeviri: Config güncelleme hatası: {e}")

        # Çeviri limiti ayarla
        if self.config.get("translation_limit") is not None:
            self.win.limit_checkbox.setChecked(True)
            self.win.limit_spinbox.setValue(self.config["translation_limit"])
        else:
            self.win.limit_checkbox.setChecked(False)

        # Config'i yeniden yükle (güncellenmiş ayarlar için)
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.win.config.read_file(f)
        except Exception:
            pass

        self.win.statusLabel.setText("Durum: 🚀 Çeviri — Başlatılıyor...")

        # Mevcut çeviri kontrolcüsünün _on_finished callback'ine workflow bitişini bağla
        # Çeviri kendi UI yönetimini yapacak, biz sadece başlatıyoruz
        original_on_finished = self.win.translation_ctrl._on_finished

        def workflow_on_finished(shutdown_requested):
            """Çeviri bittiğinde workflow'u tamamla."""
            original_on_finished(shutdown_requested)
            # Orijinal callback'i geri yükle
            self.win.translation_ctrl._on_finished = original_on_finished
            app_logger.info("Workflow Çeviri: Aşama tamamlandı.")
            QTimer.singleShot(500, self._advance_to_next_stage)

        self.win.translation_ctrl._on_finished = workflow_on_finished

        # Çeviriyi başlat
        self.win.translation_ctrl.start()

    # Tamamlanma / Hata

    def _on_workflow_completed(self):
        """Tüm aşamalar tamamlandığında çağrılır."""
        self.state = WorkflowState.COMPLETED
        app_logger.info("✅ Workflow tamamlandı — Tüm aşamalar başarıyla yürütüldü.")

        self._unlock_ui()
        self.win.progressBar.setVisible(False)
        self.win.statusLabel.setText("Durum: ✅ Workflow tamamlandı!")
        self.win.sync_database_if_exists()
        self.win.update_file_list_from_selection()

        # Kullanıcıya bildirim
        QTimer.singleShot(100, lambda: QMessageBox.information(
            self.win, "Workflow Tamamlandı",
            f"🚀 Tam Otomatik İşlem başarıyla tamamlandı!\n\n"
            f"Tamamlanan aşamalar: {len(self._stages)}\n"
            f"• {chr(10).join(self._stage_display_name(s) for s in self._stages)}"
        ))

        self._reset()

    def _on_stage_error(self, message: str):
        """Herhangi bir aşamada hata olduğunda çağrılır."""
        current_stage = self._stages[self._current_stage_index] if self._current_stage_index < len(self._stages) else "?"
        self.state = WorkflowState.ERROR

        app_logger.error(f"Workflow HATA [{current_stage}]: {message}")

        self._cleanup_thread()
        self._unlock_ui()
        self.win.progressBar.setVisible(False)
        self.win.statusLabel.setText(f"Durum: ❌ Workflow hatası — {message[:60]}")

        QTimer.singleShot(100, lambda: QMessageBox.critical(
            self.win, "Workflow Hatası",
            f"Aşama: {self._stage_display_name(current_stage)}\n\n"
            f"Hata: {message}\n\n"
            f"Workflow durduruldu. Kalan aşamalar atlandı."
        ))

        self._reset()

    # Yardımcı Metotlar 

    def _resolve_api_config(self, api_config: dict) -> tuple:
        """API/MCP konfigürasyonunu çözümler → (api_key, endpoint_id, model_version)."""
        project_path = self.config["project_path"]
        config_path = os.path.join(project_path, "config", "config.ini")
        cfg = configparser.ConfigParser()
        try:
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg.read_file(f)
        except Exception:
            pass

        api_key = cfg.get("API", "gemini_api_key", fallback=None)
        endpoint_id = cfg.get("MCP", "endpoint_id", fallback=None)
        model_version = self.win.get_gemini_model_version()

        config_type = api_config.get("type", "")
        if config_type == "project_mcp":
            endpoint_id = api_config.get("id", endpoint_id)
            api_key = None
        elif config_type == "mcp":
            endpoint_id = api_config.get("id")
            api_key = None
        elif config_type == "project_api":
            api_key = api_config.get("key", api_key)
            endpoint_id = None

        return api_key, endpoint_id, model_version

    def _on_progress(self, current, total):
        """İndirme ilerleme güncellemesi."""
        self.win.progressBar.setValue(current)
        if total > 0:
            self.win.progressBar.setMaximum(total)

    def _lock_ui(self):
        """Workflow çalışırken UI'ı kilitle."""
        self.win.startButton.setEnabled(False)
        self.win.splitButton.setEnabled(False)
        self.win.downloadMethodCombo.setEnabled(False)
        self.win.translateButton.setEnabled(False)
        self.win.mergeButton.setEnabled(False)
        self.win.projectSettingsButton.setEnabled(False)
        self.win.selectHighlightedButton.setEnabled(False)
        self.win.token_count_button.setEnabled(False)
        self.win.errorCheckButton.setEnabled(False)
        self.win.generateTerminologyButton.setEnabled(False)
        if hasattr(self.win, 'workflowButton'):
            self.win.workflowButton.setEnabled(False)
        self.win.progressBar.setVisible(True)

    def _unlock_ui(self):
        """Workflow bittiğinde UI kilidini aç."""
        self.win.startButton.setEnabled(True)
        self.win.splitButton.setEnabled(True)
        self.win.downloadMethodCombo.setEnabled(True)
        self.win.translateButton.setEnabled(True)
        self.win.mergeButton.setEnabled(True)
        self.win.epubButton.setEnabled(True)
        self.win.projectSettingsButton.setEnabled(True)
        self.win.selectHighlightedButton.setEnabled(True)
        self.win.token_count_button.setEnabled(True)
        self.win.errorCheckButton.setEnabled(True)
        self.win.generateTerminologyButton.setEnabled(True)
        if hasattr(self.win, 'workflowButton'):
            self.win.workflowButton.setEnabled(True)

    def _cleanup_thread(self):
        """QThread ve Worker referanslarını güvenle temizler."""
        if self._thread is not None:
            try:
                if self._thread.isRunning():
                    self._thread.quit()
                    self._thread.wait(5000)
            except RuntimeError:
                pass
        self._thread = None
        self._worker = None

    def _reset(self):
        """Workflow durumunu sıfırlar."""
        self._cleanup_thread()
        self.state = WorkflowState.IDLE
        self.config = {}
        self._stages = []
        self._current_stage_index = -1

    def is_running(self) -> bool:
        return self.state not in (WorkflowState.IDLE, WorkflowState.COMPLETED, WorkflowState.ERROR)

    def stop(self):
        """Workflow'u durdurur (closeEvent için)."""
        if self._worker:
            try:
                if hasattr(self._worker, 'stop'):
                    self._worker.stop()
                elif hasattr(self._worker, 'is_running'):
                    self._worker.is_running = False
            except RuntimeError:
                pass
        self._reset()
