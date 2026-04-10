"""
DownloadController — İndirme işlemi iş mantığı kontrolcüsü.

Sorumluluklar:
  - İndirme thread/worker oluşturma ve yaşam döngüsü yönetimi
  - JS dosya varlığı kontrolü
  - İndirme sinyallerinin UI'ya yönlendirilmesi
"""

import os
from PyQt6.QtCore import QThread
from PyQt6.QtWidgets import QMessageBox

from core.workers.download_worker import DownloadWorker
from dialogs import SeleniumMenuDialog
from logger import app_logger
from core.file_list_manager import FileListManager


class DownloadController:
    """İndirme işlemlerini yönetir."""

    def __init__(self, main_window):
        self.win = main_window
        self.thread = None
        self.worker = None
        self.selenium_dialog = None
        self._download_succeeded = False

    def start(self):
        """İndirme işlemini başlatır."""
        current_item = self.win.project_list.currentItem()
        if not current_item:
            QMessageBox.warning(self.win, "Proje Seçilmedi", "Lütfen sol listeden bir proje seçin.")
            return

        project_name = current_item.text()
        project_path = os.path.join(os.getcwd(), project_name)
        config_path = os.path.join(project_path, 'config', 'config.ini')
        if not os.path.exists(config_path):
            QMessageBox.critical(self.win, "Hata", f"'{project_name}' projesi için config.ini bulunamadı. Lütfen projeyi yeniden oluşturun veya linki manuel girin.")
            return

        try:
            self.win.config.read(config_path)
            project_link = self.win.config.get('ProjectInfo', 'link', fallback=None)
            max_pages = self.win.config.getint('ProjectInfo', 'max_pages', fallback=None)

            if not project_link:
                QMessageBox.critical(self.win, "Hata", "Config dosyasında proje linki bulunamadı!")
                return
        except Exception as e:
            QMessageBox.critical(self.win, "Config Hatası", f"Config dosyası okunurken hata oluştu:\n{e}")
            return

        download_folder = os.path.join(project_path, 'dwnld')
        os.makedirs(download_folder, exist_ok=True)

        # Önceki indirme tamamlanmamışsa durdur
        self._stop_existing()

        # JS Script Yolu Belirleme
        js_script_path = self._resolve_js_script()
        if js_script_path is False:
            return  # Kullanıcıya hata gösterildi

        self.thread = QThread()
        self.worker = DownloadWorker(project_link, download_folder, max_pages, js_script_path)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self._download_succeeded = False
        self.worker.file_downloaded.connect(self._on_file_downloaded)
        self.worker.error.connect(self._on_error)
        self.worker.finished.connect(self._on_finished)
        self.worker.progress.connect(self._on_progress)
        self.worker.selenium_menu_required.connect(self._handle_selenium_menu)

        self.thread.start()

        if js_script_path:
            self.win._set_ui_state_on_process_start(self.win.startButton, "İndiriliyor (Tarayıcı)...", "#FFC107", "black", 100, "Durum: Tarayıcı ile indiriliyor...")
        else:
            self.win._set_ui_state_on_process_start(self.win.startButton, "İndiriliyor...", "#FFC107", "black", max_pages if max_pages else 0, "Durum: İndirme işlemi başlatıldı...")

        self.win.file_table.setRowCount(0)

    def _resolve_js_script(self):
        """İndirme yöntemine göre JS script yolunu belirler. Hata durumunda False döner."""
        selected_method = self.win.downloadMethodCombo.currentText()
        js_files = {
            "Booktoki": "booktoki.js",
            "69shuba": "69shuba.js",
            "Novelfire": "novelfire.js",
        }

        for key, filename in js_files.items():
            if key in selected_method:
                js_script_path = os.path.join(os.getcwd(), filename)
                if not os.path.exists(js_script_path):
                    try:
                        from core.js_create import create_js_file
                        create_js_file(filename)
                    except Exception:
                        pass
                if not os.path.exists(js_script_path):
                    QMessageBox.warning(self.win, "Dosya Bulunamadı", f"{filename} dosyası mevcut dizinde bulunamadı!")
                    return False
                return js_script_path

        return None  # Normal Web Kazıma

    def _on_progress(self, current, total):
        self.win.progressBar.setValue(current)
        if total > 0:
            self.win.progressBar.setMaximum(total)
            self.win.statusLabel.setText(f"Durum: İndiriliyor... Sayfa {current}/{total}")
        else:
            self.win.statusLabel.setText(f"Durum: İndiriliyor... Sayfa {current}")

    def _handle_selenium_menu(self):
        """Selenium worker'dan gelen menü isteğini işler."""
        if not self.worker:
            return
        self.selenium_dialog = SeleniumMenuDialog(self.worker, self.win)
        self.selenium_dialog.finished.connect(self._on_selenium_dialog_closed)
        self.selenium_dialog.exec()

    def _on_selenium_dialog_closed(self):
        """Selenium diyaloğu kullanıcı tarafından normal (İptal) ile kapandığında UI'yı günceller."""
        app_logger.info("DownloadController: Selenium diyaloğu kapandı, UI güncelleniyor.")
        self.win._set_ui_state_on_process_end(self.win.startButton, "İndirmeyi Başlat", "#4CAF50", "white", "Durum: Hazır")
        self._reset_state()
        self.win.sync_database_if_exists()
        self.win.update_file_list_from_selection()

    def _on_file_downloaded(self, file_path, filename):
        """İndirilen dosyayı tabloya ekler ve UI günceller."""
        app_logger.info(f"DownloadController: Dosya indirildi: {filename}")
        self._download_succeeded = True
        self.win.sync_database_if_exists()
        self.win.update_file_list_from_selection()

    def _on_finished(self):
        """Worker finished sinyalini işler."""
        dialog_active = (
            hasattr(self, 'selenium_dialog')
            and self.selenium_dialog
            and self.selenium_dialog.isVisible()
        )

        if dialog_active:
            app_logger.info("DownloadController: finished sinyali alındı (Diyalog aktif).")
            self.selenium_dialog.close()
            if self._download_succeeded:
                # Dosya başarıyla indirilmiş, normal tamamlanma akışı
                app_logger.info("DownloadController: İndirme başarıyla tamamlandı (diyalog kapalıyor).")
                QMessageBox.information(self.win, "Tamamlandı", "İndirme işlemi başarıyla tamamlandı.")
                self.win._set_ui_state_on_process_end(self.win.startButton, "İndirmeyi Başlat", "#4CAF50", "white", "Durum: Hazır")
            else:
                # Dosya indirilmeden Selenium kapandı
                app_logger.error("DownloadController: Tarayıcı indirme tamamlanmadan kapandı.")
                QMessageBox.warning(
                    self.win,
                    "Tarayıcı Beklenmedik Kapandı",
                    "Tarayıcı indirme tamamlanmadan kapandı.\n"
                    "Sebep log dosyasına kaydedildi.\n\n"
                    "İşlemi tekrarlamak için 'İndirmeyi Başlat' tuşuna basın."
                )
                self.win._set_ui_state_on_process_end(self.win.startButton, "İndirmeyi Başlat", "#FF5722", "white", "Durum: Tarayıcı beklenmedik kapandı")
            self._reset_state()
            self.win.sync_database_if_exists()
            self.win.update_file_list_from_selection()
            return

        app_logger.info("DownloadController: İndirme işlemi başarıyla tamamlandı.")
        QMessageBox.information(self.win, "Tamamlandı", "İndirme işlemi bitti.")
        self.win._set_ui_state_on_process_end(self.win.startButton, "İndirmeyi Başlat", "#4CAF50", "white", "Durum: Hazır")
        self._reset_state()
        self.win.sync_database_if_exists()
        self.win.update_file_list_from_selection()

    def _on_error(self, message):
        """Worker hata sinyalini işler — diyalog açık olsa bile gösterir."""
        app_logger.error(f"DownloadController: İndirme hatası: {message}")
        dialog_active = (
            hasattr(self, 'selenium_dialog')
            and self.selenium_dialog
            and self.selenium_dialog.isVisible()
        )
        if dialog_active:
            self.selenium_dialog.close()
        QMessageBox.critical(
            self.win,
            "İndirme Hatası",
            f"Bir hata oluştu:\n{message}\n\n"
            f"Sebep log dosyasına kaydedildi.\n"
            f"Lütfen 'İndirmeyi Başlat' tuşuna basarak işlemi tekrar başlatın."
        )
        self.win._set_ui_state_on_process_end(self.win.startButton, "İndirmeyi Başlat", "#FF5722", "white", f"Durum: Hata - {message}")
        self._reset_state()


    def _reset_state(self):
        """Thread, worker ve diyalog referanslarını temizler."""
        self.thread = None
        self.worker = None
        self.selenium_dialog = None

    def _stop_existing(self):
        """Çalışan bir indirme varsa durdurur."""
        if self.thread and self.thread.isRunning():
            self.worker.stop()
            self.thread.quit()
            self.thread.wait()
            self.thread = None
            self.worker = None

    def is_running(self):
        return self.thread is not None and self.thread.isRunning()

    def stop(self):
        """İndirmeyi durdurur (closeEvent için)."""
        if self.worker:
            self.worker.stop()

