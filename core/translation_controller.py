"""
TranslationController — Çeviri işlemi iş mantığı kontrolcüsü.

Sorumluluklar:
  - Çeviri thread/worker oluşturma ve yaşam döngüsü yönetimi
  - Duraklatma / devam etme / durdurma mantığı
  - Çeviri bittiğinde shutdown kontrolü
"""

import os
import sys
import configparser
from PyQt6.QtCore import QThread, QTimer
from PyQt6.QtWidgets import QMessageBox

from core.workers.translation_worker import TranslationWorker
from logger import app_logger


class TranslationController:
    """Çeviri işlemlerini yönetir."""

    def __init__(self, main_window):
        self.win = main_window
        self.thread = None
        self.worker = None
        self._has_error = False

    # --- Güvenli QThread Geçerlilik Kontrolü -------------------------------
    def _is_thread_alive(self):
        """QThread hâlâ geçerli ve çalışıyor mu? C++ deletion güvenli."""
        if self.thread is None:
            return False
        try:
            return self.thread.isRunning()
        except RuntimeError:
            # C++ nesnesi silinmiş ama Python referansı hâlâ duruyor
            self.thread = None
            self.worker = None
            return False

    def _cleanup(self):
        """Thread ve Worker referanslarını güvenle serbest bırakır."""
        self.thread = None
        self.worker = None
        self._has_error = False

    # --- Başlatma ----------------------------------------------------------
    def start(self):
        """Çeviri işlemini başlatır veya duraklatma/devam işlemini yönetir."""
        if self._is_thread_alive():
            self._toggle_pause()
            return

        # Ölü referans temizliği (deleteLater gecikmeli silebilir)
        if self.thread is not None:
            self._cleanup()

        current_item = self.win.project_list.currentItem()
        if not current_item:
            QMessageBox.warning(self.win, "Proje Seçilmedi", "Lütfen sol listeden bir proje seçin.")
            return

        project_name = current_item.text()
        project_path = os.path.join(os.getcwd(), project_name)
        config_path = os.path.join(project_path, 'config', 'config.ini')
        if not os.path.exists(config_path):
            QMessageBox.critical(self.win, "Hata", f"'{project_name}' projesi için config.ini bulunamadı. API anahtarı okunamıyor.")
            return

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.win.config.read_file(f)
            api_key = self.win.config.get('API', 'gemini_api_key', fallback=None)
            api_key_name = self.win.config.get('API', 'api_key_name', fallback='Varsayılan')
            startpromt = self.win.config.get('Startpromt', 'startpromt', fallback=None)
            mcp_endpoint_id = self.win.config.get('MCP', 'endpoint_id', fallback=None)
            translation_provider = self.win.config.get('API', 'translation_provider', fallback='llm')

            if translation_provider == 'llm' and not api_key and not mcp_endpoint_id:
                QMessageBox.critical(self.win, "Yapılandırma Eksik", "Seçili proje için API anahtarı veya MCP bağlantısı bulunamadı. Lütfen proje ayarlarından yapılandırın.")
                return
        except configparser.Error as e:
            QMessageBox.critical(self.win, "Config Hatası", f"Config dosyası okunurken hata oluştu:\n{e}")
            return
        except Exception as e:
            QMessageBox.critical(self.win, "Genel Hata", f"API anahtarı okunurken beklenmeyen bir hata oluştu:\n{e}")
            return

        input_folder = os.path.join(project_path, 'dwnld')
        output_folder = os.path.join(project_path, 'trslt')
        os.makedirs(output_folder, exist_ok=True)

        files_to_translate = [f for f in os.listdir(input_folder) if f.endswith('.txt')]
        if not files_to_translate:
            QMessageBox.information(self.win, "Dosya Yok", "İndirilenler klasöründe çevrilecek dosya bulunamadı.")
            return

        model_version = self.win.get_gemini_model_version()
        self._stop_existing()

        file_limit = None
        if self.win.limit_checkbox.isChecked():
            file_limit = self.win.limit_spinbox.value()

        max_retries = self.win.config.getint('ProjectInfo', 'max_retries', fallback=3)
        cache_enabled = self.win.config.getboolean('Features', 'cache_enabled', fallback=True)
        terminology_enabled = self.win.config.getboolean('Features', 'terminology_enabled', fallback=True)
        async_enabled = self.win.config.getboolean('Features', 'async_enabled', fallback=False)
        async_threads = self.win.config.getint('Features', 'async_threads', fallback=3)
        batch_enabled = self.win.config.getboolean('Batch', 'batch_enabled', fallback=False)
        max_batch_chars = self.win.config.getint('Batch', 'max_batch_chars', fallback=33000)
        max_chapters_per_batch = self.win.config.getint('Batch', 'max_chapters_per_batch', fallback=5)

        self.thread = QThread()
        self.worker = TranslationWorker(
            input_folder, output_folder, api_key, startpromt, model_version,
            file_limit=file_limit, max_retries=max_retries, project_path=project_path,
            cache_enabled=cache_enabled, terminology_enabled=terminology_enabled,
            endpoint_id=mcp_endpoint_id, async_enabled=async_enabled, async_threads=async_threads,
            batch_enabled=batch_enabled, max_batch_chars=max_batch_chars,
            max_chapters_per_batch=max_chapters_per_batch,
            translation_provider=translation_provider,
        )

        self.worker.shutdown_on_finish = self.win.shutdown_checkbox.isChecked()
        self._has_error = False
        self.worker.moveToThread(self.thread)

        # NOT: deleteLater KULLANILMIYOR — C++ erken silme sorununu önlemek için
        # referanslar thread.finished sinyali ile güvenle temizleniyor.
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.progress.connect(self._on_progress)
        self.worker.request_made.connect(self._on_request_made)
        # Thread GERÇEKTEN durduğunda referansları temizle
        self.thread.finished.connect(self._on_thread_done)

        self.thread.start()

        # Buton durumlarını ayarla
        self.win.startButton.setEnabled(False)
        self.win.mergeButton.setEnabled(False)
        self.win.errorCheckButton.setEnabled(False)
        self.win.projectSettingsButton.setEnabled(False)
        self.win.token_count_button.setEnabled(False)
        self.win.stopTranslationButton.setVisible(True)

        self.win.translateButton.setEnabled(True)
        self.win.translateButton.setText("Duraklat")
        self.win.translateButton.setStyleSheet("background-color: #FFC107; color: black; border-radius: 5px; padding: 10px;")

        self.win.progressBar.setValue(0)
        self.win.progressBar.setMaximum(len(files_to_translate))
        self.win.progressBar.setVisible(True)

        display_model = model_version
        if mcp_endpoint_id:
            try:
                from core.llm_provider import load_endpoints
                eps = load_endpoints().get("endpoints", [])
                for ep in eps:
                    if ep["id"] == mcp_endpoint_id:
                        display_model = f"{ep['name']} ({ep['model_id']})"
                        api_key_name = ep["type"]
                        break
            except:
                pass
        self.win.statusLabel.setText(f"Durum: Çeviri başlatıldı... (Model: {display_model})")

        # Status bar güncelle
        self.win._current_model = display_model
        self.win._current_api_name = api_key_name
        self.win._current_status = "Çeviri yapılıyor"
        self.win.update_status_bar()

    # --- Duraklatma / Devam ------------------------------------------------
    def _toggle_pause(self):
        if self.worker.is_paused:
            self.worker.resume()
            self.win.translateButton.setText("Duraklat")
            self.win.translateButton.setStyleSheet("background-color: #FFC107; color: black; border-radius: 5px; padding: 10px;")
            self.win.statusLabel.setText("Durum: Çeviriye devam ediliyor...")
        else:
            self.worker.pause()
            self.win.translateButton.setText("Devam Et")
            self.win.translateButton.setStyleSheet("background-color: #4CAF50; color: white; border-radius: 5px; padding: 10px;")
            self.win.statusLabel.setText("Durum: Çeviri duraklatıldı.")

    # --- Signal Handler'lar ------------------------------------------------
    def _on_progress(self, current, total):
        self.win.progressBar.setValue(current)
        self.win.progressBar.setMaximum(total)
        self.win.statusLabel.setText(f"Durum: Çevriliyor... Dosya {current}/{total}")

    def _on_request_made(self):
        self.win.request_counter_manager.increment(self.win._current_model, self.win._current_api_name)
        self.win.update_status_bar()

    def _restore_ui(self):
        """Çeviri bittikten sonra UI butonlarını sıfırlar."""
        self.win.startButton.setEnabled(True)
        self.win.translateButton.setEnabled(True)
        self.win.mergeButton.setEnabled(True)
        self.win.epubButton.setEnabled(True)
        self.win.projectSettingsButton.setEnabled(True)
        self.win.token_count_button.setEnabled(True)
        self.win.errorCheckButton.setEnabled(True)
        self.win.translateButton.setText("Seçilenleri Çevir")
        self.win.translateButton.setStyleSheet("background-color: #2196F3; color: white; border-radius: 5px; padding: 10px;")
        self.win.progressBar.setVisible(False)
        self.win.stopTranslationButton.setVisible(False)

    def _on_thread_done(self):
        """QThread kapandığında (finished sinyali) referansları güvenle temizler."""
        app_logger.info("TranslationController: QThread kapandı, referanslar temizleniyor.")
        self.thread = None
        self.worker = None
        self._has_error = False

    def _on_finished(self, shutdown_requested):
        if self._has_error:
            # _on_error zaten UI'ı düzeltti; DB senkronizasyonunu yap
            try:
                self.win.sync_database_if_exists()
                self.win.update_file_list_from_selection()
            except Exception:
                pass
            return

        translated_count = self.win.progressBar.value()
        self._restore_ui()
        self.win.statusLabel.setText("Durum: Hazır")
        self.win.sync_database_if_exists()
        self.win.update_file_list_from_selection()
        self.win._current_status = "Hazır"
        self.win.update_status_bar()
        self.win._notify_translation_complete(translated_count)

        # Referans temizliği _on_thread_done'da yapılacak (thread bitince)
        # Burada _cleanup() ÇAĞIRMA — thread hâlâ kapanıyor olabilir

        # Mesajı ve shutdown'u olay döngüsü serbest kaldıktan sonra göster
        QTimer.singleShot(50, lambda: QMessageBox.information(self.win, "Tamamlandı", "Çeviri işlemi bitti."))

        if shutdown_requested:
            def handle_shutdown():
                reply = QMessageBox.question(self.win, 'Bilgisayar Kapatılıyor',
                                             "Çeviri tamamlandı. Bilgisayar 60 saniye içinde kapatılacak.\nİptal etmek istiyor musunuz?",
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                             QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.Yes:
                    self._cancel_shutdown()
                else:
                    self._shutdown_computer()
            QTimer.singleShot(100, handle_shutdown)

    def _on_error(self, message):
        self._has_error = True
        app_logger.error(f"TranslationController: Çeviri hatası sinyali alındı — {message}")

        self._restore_ui()
        self.win.statusLabel.setText(f"Durum: Hata — {message[:80]}")

        # NOT: _cleanup() ÇAĞIRMA — thread hâlâ çalışıyor olabilir!
        # Referans temizliği _on_thread_done'da (thread.finished sinyalinde) yapılacak.

        self.win.sync_database_if_exists()
        self.win.update_file_list_from_selection()

        QTimer.singleShot(50, lambda: QMessageBox.critical(
            self.win, "Çeviri Hatası", f"Bir hata oluştu:\n{message}"
        ))

    # --- Dışarıdan Durdurma ------------------------------------------------
    def stop_translation(self):
        """Çeviriyi tamamen durdurur (UI onaylı)."""
        if not self._is_thread_alive():
            return

        reply = QMessageBox.question(
            self.win, 'Çeviriyi Durdur',
            "Çeviri işlemini durdurmak istediğinize emin misiniz?\nTüm çevrilen dosyalar korunacaktır.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            if self.worker:
                self.worker.stop()
            self.win.statusLabel.setText("Durum: Çeviri durduruluyor...")
            self.win.stopTranslationButton.setEnabled(False)

    def _shutdown_computer(self):
        try:
            if sys.platform == "win32":
                os.system("shutdown /s /t 60")
            elif sys.platform == "darwin":
                os.system("sudo shutdown -h +1")
            else:
                os.system("shutdown +1")
        except Exception as e:
            QMessageBox.critical(self.win, "Hata", str(e))

    def _cancel_shutdown(self):
        try:
            if sys.platform == "win32":
                os.system("shutdown /a")
        except Exception:
            pass

    def _stop_existing(self):
        """Çalışan bir çeviri varsa durdurur."""
        if self._is_thread_alive():
            if self.worker:
                self.worker.stop()
            self.thread.quit()
            self.thread.wait(3000)
        self._cleanup()

    def is_running(self):
        return self._is_thread_alive()

    def stop(self):
        """Çeviriyi durdurur (closeEvent için)."""
        if self.worker:
            try:
                self.worker.stop()
            except RuntimeError:
                pass
