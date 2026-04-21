"""
ProcessController — Küçük ölçekli işlem kontrolcüleri.

İçerir:
  - CleaningController: Temizleme işlemi
  - SplitController: Dosya bölme işlemi
  - EpubController: EPUB oluşturma işlemi
  - ErrorCheckController: Çeviri hata kontrolü
  - ChapterCheckController: Başlık kontrolü
  - MLTerminologyController: YZ terminoloji üretimi
"""

import os
from PyQt6.QtCore import Qt, QThread
from PyQt6.QtWidgets import QMessageBox, QFileDialog

from core.workers.cleaning_worker import CleaningWorker
from core.workers.split_worker import SplitWorker
from core.workers.epub_worker import EpubWorker
from core.chapter_check_worker import ChapterCheckWorker
from core.workers.translation_error_check_worker import TranslationErrorCheckWorker
from core.workers.ml_terminology_worker import MLTerminologyWorker
from core.utils import natural_sort_key


class CleaningController:
    """Temizleme işlemlerini yönetir."""

    def __init__(self, main_window):
        self.win = main_window
        self.thread = None
        self.worker = None

    def start(self):
        current_item = self.win.project_list.currentItem()
        if not current_item:
            QMessageBox.warning(self.win, "Proje Seçilmedi", "Lütfen sol listeden bir proje seçin.")
            return
        project_name = current_item.text()
        project_path = os.path.join(os.getcwd(), project_name)

        selected_file_paths = []
        for row in range(self.win.file_table.rowCount()):
            checkbox_item = self.win.file_table.item(row, 0)
            if checkbox_item and checkbox_item.checkState() == Qt.CheckState.Checked:
                original_file_name = self.win.file_table.item(row, 1).text()
                translated_file_name = self.win.file_table.item(row, 2).text()

                if translated_file_name and translated_file_name != "Yok":
                    file_path = os.path.join(project_path, 'trslt', translated_file_name)
                    if os.path.exists(file_path):
                        selected_file_paths.append(file_path)
                elif original_file_name and original_file_name != "Orijinali Yok":
                    file_path = os.path.join(project_path, 'dwnld', original_file_name)
                    if os.path.exists(file_path):
                        selected_file_paths.append(file_path)

        if not selected_file_paths:
            QMessageBox.warning(self.win, "Dosya Seçilmedi", "Lütfen temizlemek için en az bir dosya seçin.")
            return

        self._stop_existing()

        self.thread = QThread()
        self.worker = CleaningWorker(selected_file_paths, os.path.join(project_path, 'trslt'))
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.progress.connect(self._on_progress)
        self.thread.start()

        self.win.startButton.setEnabled(False)
        self.win.translateButton.setEnabled(False)
        self.win.mergeButton.setEnabled(False)
        self.win.projectSettingsButton.setEnabled(False)
        self.win.token_count_button.setEnabled(False)
        self.win.progressBar.setValue(0)
        self.win.progressBar.setMaximum(len(selected_file_paths))
        self.win.progressBar.setVisible(True)
        self.win.statusLabel.setText(f"Durum: {len(selected_file_paths)} dosya temizleniyor...")

    def _on_progress(self, current, total):
        self.win.progressBar.setValue(current)
        self.win.progressBar.setMaximum(total)
        self.win.statusLabel.setText(f"Durum: Temizleniyor... Dosya {current}/{total}")

    def _on_finished(self):
        QMessageBox.information(self.win, "Tamamlandı", "Metin temizleme işlemi bitti.")
        self._restore_buttons()
        self.win.progressBar.setVisible(False)
        self.win.statusLabel.setText("Durum: Hazır")
        self.thread = None
        self.worker = None
        self.win.sync_database_if_exists()
        self.win.update_file_list_from_selection()

    def _on_error(self, message):
        QMessageBox.critical(self.win, "Temizleme Hatası", f"Bir hata oluştu:\n{message}")
        self._restore_buttons()
        self.win.progressBar.setVisible(False)
        self.win.statusLabel.setText(f"Durum: Hata - {message}")
        self.thread = None
        self.worker = None
        self.win.sync_database_if_exists()
        self.win.update_file_list_from_selection()

    def _restore_buttons(self):
        self.win.startButton.setEnabled(True)
        self.win.translateButton.setEnabled(True)
        self.win.mergeButton.setEnabled(True)
        self.win.epubButton.setEnabled(True)
        self.win.projectSettingsButton.setEnabled(True)
        self.win.token_count_button.setEnabled(True)
        self.win.errorCheckButton.setEnabled(True)

    def _stop_existing(self):
        if self.thread and self.thread.isRunning():
            self.worker.stop()
            self.thread.quit()
            self.thread.wait()
            self.thread = None
            self.worker = None

    def is_running(self):
        return self.thread is not None and self.thread.isRunning()

    def stop(self):
        if self.worker:
            self.worker.stop()


class SplitController:
    """Dosya bölme işlemlerini yönetir."""

    def __init__(self, main_window):
        self.win = main_window
        self.thread = None
        self.worker = None

    def start(self):
        current_item = self.win.project_list.currentItem()
        if not current_item:
            QMessageBox.warning(self.win, "Proje Seçilmedi", "Lütfen sol listeden bir proje seçin.")
            return
        project_name = current_item.text()
        project_path = os.path.join(os.getcwd(), project_name)

        input_file_path, _ = QFileDialog.getOpenFileName(
            self.win, "Bölünecek TXT Dosyasını Seçin", "",
            "Text Dosyaları (*.txt);;Tüm Dosyalar (*)"
        )
        if not input_file_path:
            return

        output_folder = os.path.join(project_path, 'dwnld')
        os.makedirs(output_folder, exist_ok=True)
        self._stop_existing()

        self.thread = QThread()
        self.worker = SplitWorker(input_file_path, output_folder)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.progress.connect(self._on_progress)
        self.thread.start()
        self.win._set_ui_state_on_process_start(self.win.splitButton, "Bölünüyor...", "#FFC107", "black", 100, "Durum: Dosya parçalanıyor...")

    def _on_progress(self, current, total):
        self.win.progressBar.setValue(current)
        if total > 0:
            self.win.progressBar.setMaximum(total)
            self.win.statusLabel.setText(f"Durum: Parçalanıyor... {current}/{total} bölüm oluşturuldu")

    def _on_finished(self):
        QMessageBox.information(self.win, "Tamamlandı", "Dosya başarıyla parçalandı ve projeye eklendi.")
        self.win._set_ui_state_on_process_end(self.win.splitButton, "Toplu Bölüm Ekle", "#3F51B5", "white", "Durum: Hazır")
        self.thread = None
        self.worker = None
        self.win.sync_database_if_exists()
        self.win.update_file_list_from_selection()

    def _on_error(self, message):
        QMessageBox.critical(self.win, "Parçalama Hatası", f"Bir hata oluştu:\n{message}")
        self.win._set_ui_state_on_process_end(self.win.splitButton, "Toplu Bölüm Ekle", "#FF5722", "white", f"Durum: Hata - {message}")
        self.thread = None
        self.worker = None

    def _stop_existing(self):
        if self.thread and self.thread.isRunning():
            self.worker.stop()
            self.thread.quit()
            self.thread.wait()
            self.thread = None
            self.worker = None

    def is_running(self):
        return self.thread is not None and self.thread.isRunning()

    def stop(self):
        if self.worker:
            self.worker.stop()


class EpubController:
    """EPUB oluşturma işlemlerini yönetir."""

    def __init__(self, main_window):
        self.win = main_window
        self.thread = None
        self.worker = None

    def start(self):
        current_item = self.win.project_list.currentItem()
        if not current_item:
            QMessageBox.warning(self.win, "Proje Seçilmedi", "Lütfen sol listeden bir proje seçin.")
            return
        project_name = current_item.text()
        project_path = os.path.join(os.getcwd(), project_name)

        selected_files = []
        for row in range(self.win.file_table.rowCount()):
            checkbox_item = self.win.file_table.item(row, 0)
            if checkbox_item and checkbox_item.checkState() == Qt.CheckState.Checked:
                translated_file_name = self.win.file_table.item(row, 2).text()
                if translated_file_name and translated_file_name not in ["Yok", "N/A"]:
                    file_path = os.path.join(project_path, 'trslt', translated_file_name)
                    if os.path.exists(file_path):
                        selected_files.append(file_path)

        if not selected_files:
            QMessageBox.warning(self.win, "Dosya Seçilmedi", "Lütfen EPUB yapmak için en az bir çevrilmiş dosya seçin.")
            return

        selected_files.sort(key=lambda x: natural_sort_key(os.path.basename(x)))
        self._stop_existing()

        output_folder = os.path.join(project_path, 'cmplt')
        os.makedirs(output_folder, exist_ok=True)

        self.thread = QThread()
        self.worker = EpubWorker(selected_files, output_folder, project_name=project_name)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.progress.connect(self._on_progress)
        self.thread.start()
        self.win._set_ui_state_on_process_start(
            self.win.epubButton, "Epub Oluşturuluyor...", "#FFC107", "black",
            len(selected_files), "Durum: EPUB dosyası oluşturuluyor..."
        )

    def _on_progress(self, current, total):
        self.win.progressBar.setValue(current)
        self.win.progressBar.setMaximum(total)
        self.win.statusLabel.setText(f"Durum: EPUB Bölümleri Ekleniyor... {current}/{total}")

    def _on_finished(self, message):
        if message:
            QMessageBox.information(self.win, "Tamamlandı", message)
        self.win._set_ui_state_on_process_end(
            self.win.epubButton, "Seçilenleri EPUB Yap", "#795548", "white", "Durum: Hazır"
        )
        self.thread = None
        self.worker = None
        self.win.sync_database_if_exists()
        self.win.update_file_list_from_selection()

    def _on_error(self, message):
        QMessageBox.critical(self.win, "Hata", message)
        self.win._set_ui_state_on_process_end(
            self.win.epubButton, "Seçilenleri EPUB Yap", "#FF5722", "white", f"Durum: Hata - {message}"
        )
        self.thread = None
        self.worker = None

    def _stop_existing(self):
        if self.thread and self.thread.isRunning():
            self.worker.stop()
            self.thread.quit()
            self.thread.wait()
            self.thread = None
            self.worker = None

    def is_running(self):
        return self.thread is not None and self.thread.isRunning()

    def stop(self):
        if self.worker:
            self.worker.stop()


class ErrorCheckController:
    """Çeviri hata kontrolü işlemlerini yönetir."""

    def __init__(self, main_window):
        self.win = main_window
        self.thread = None
        self.worker = None

    def start(self):
        if not self.win.current_project_path:
            QMessageBox.warning(self.win, "Proje Seçilmedi", "Lütfen bir proje seçin.")
            return
        trslt_folder = os.path.join(self.win.current_project_path, 'trslt')
        if not os.path.exists(trslt_folder):
            QMessageBox.warning(self.win, "Klasör Yok", "Çeviri klasörü (trslt) bulunamadı.")
            return

        report_folder = os.path.join(self.win.current_project_path, 'trslt', 'hata_kontrol')
        self.win._set_all_buttons_enabled_state(False)
        self.win.statusLabel.setText("Durum: Çeviri hata kontrolü yapılıyor...")
        self.win.progressBar.setValue(0)
        self.win.progressBar.setMaximum(0)
        self.win.progressBar.setVisible(True)

        self.thread = QThread()
        self.worker = TranslationErrorCheckWorker(trslt_folder, report_folder)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def _on_progress(self, current, total):
        self.win.progressBar.setMaximum(total)
        self.win.progressBar.setValue(current)
        self.win.statusLabel.setText(f"Durum: Hata kontrolü... Dosya {current}/{total}")

    def _on_finished(self, results):
        self.win._set_all_buttons_enabled_state(True)
        self.win.progressBar.setVisible(False)
        self.win.statusLabel.setText("Durum: Hazır")

        high = results.get("high", [])
        low = results.get("low", [])
        report_path = results.get("report_path", "")

        if not high:
            QMessageBox.information(
                self.win, "Hata Kontrolü Tamamlandı",
                f"Hiçbir çevrilmiş dosyada yüksek Korece/Çince karakter oranı bulunamadı.\n"
                f"Düşük oranlı dosya sayısı: {len(low)}\n"
                f"Rapor: {report_path}"
            )
        else:
            file_list_str = "\n".join([
                f"  - {f['filename']} (Korece: {f['korean_ratio']*100:.1f}%, Çince: {f['chinese_ratio']*100:.1f}%)"
                for f in high[:20]
            ])
            reply = QMessageBox.question(
                self.win, 'Çeviri Hata Kontrolü',
                f"Yüksek Korece/Çince oranı bulunan {len(high)} dosya var:\n\n"
                f"{file_list_str}\n\n"
                f"Bu dosyaları silmek istiyor musunuz?\n"
                f"(Raporlar {report_path} içinde kaydedildi)",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                deleted_count = 0
                for f_info in high:
                    try:
                        os.remove(f_info['filepath'])
                        deleted_count += 1
                    except Exception:
                        pass
                QMessageBox.information(self.win, "Silindi", f"{deleted_count} dosya silindi.")
                self.win.sync_database_if_exists()
                self.win.update_file_list_from_selection()

        self.thread = None
        self.worker = None

    def _on_error(self, message):
        self.win._set_all_buttons_enabled_state(True)
        self.win.progressBar.setVisible(False)
        self.win.statusLabel.setText("Durum: Hazır")
        QMessageBox.critical(self.win, "Hata Kontrol Hatası", message)
        self.thread = None
        self.worker = None

    def is_running(self):
        return self.thread is not None and self.thread.isRunning()

    def stop(self):
        if self.worker:
            self.worker.stop()


class ChapterCheckController:
    """Başlık kontrolü işlemlerini yönetir."""

    def __init__(self, main_window):
        self.win = main_window
        self.thread = None
        self.worker = None

    def start(self):
        current_item = self.win.project_list.currentItem()
        if not current_item:
            QMessageBox.warning(self.win, "Proje Seçilmedi", "Lütfen sol listeden bir proje seçin.")
            return
        project_name = current_item.text()
        project_path = os.path.join(os.getcwd(), project_name)

        files_to_check = []
        for row in range(self.win.file_table.rowCount()):
            checkbox_item = self.win.file_table.item(row, 0)
            if checkbox_item and checkbox_item.checkState() == Qt.CheckState.Checked:
                translated_file_name = self.win.file_table.item(row, 2).text()
                if translated_file_name and translated_file_name != "Yok" and translated_file_name != "N/A":
                    file_path = os.path.join(project_path, 'trslt', translated_file_name)
                    files_to_check.append((translated_file_name, file_path))

        if not files_to_check:
            QMessageBox.warning(self.win, "Dosya Seçilmedi", "Lütfen başlık kontrolü için en az bir çevrilmiş dosya seçin.")
            return

        self._stop_existing()

        self.thread = QThread()
        self.worker = ChapterCheckWorker(project_path, files_to_check)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.finished.connect(self._on_finished)
        self.worker.progress.connect(self._on_progress)
        self.worker.error.connect(self._on_error)
        self.thread.start()

    def _on_progress(self, current, total):
        self.win.progressBar.setValue(current)
        self.win.progressBar.setMaximum(total)
        self.win.statusLabel.setText(f"Durum: Kontrol ediliyor... Dosya {current}/{total}")

    def _on_finished(self, message):
        QMessageBox.information(self.win, "Tamamlandı", message)
        self.thread = None
        self.worker = None

    def _on_error(self, message):
        QMessageBox.critical(self.win, "Hata", message)
        self.thread = None
        self.worker = None

    def _stop_existing(self):
        if self.thread and self.thread.isRunning():
            self.worker.stop()
            self.thread.quit()
            self.thread.wait()
            self.thread = None
            self.worker = None

    def is_running(self):
        return self.thread is not None and self.thread.isRunning()

    def stop(self):
        if self.worker:
            self.worker.stop()


class MLTerminologyController:
    """YZ terminoloji üretimi işlemlerini yönetir."""

    def __init__(self, main_window):
        self.win = main_window
        self.thread = None

    def start(self):
        current_item = self.win.project_list.currentItem()
        if not current_item:
            QMessageBox.warning(self.win, "Proje Seçilmedi", "Lütfen sol listeden bir proje seçin.")
            return
        project_name = current_item.text()
        project_path = os.path.join(os.getcwd(), project_name)

        if self.thread and self.thread.isRunning():
            QMessageBox.warning(self.win, "Çalışıyor", "Terminoloji işlemi zaten devam ediyor.")
            return

        # ── Bölüm Aralığı Diyalogunu Aç ──
        from ui.ml_terminology_range_dialog import MLTerminologyRangeDialog
        from PyQt6.QtWidgets import QDialog
        dlg = MLTerminologyRangeDialog(project_path, parent=self.win)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return  # Kullanıcı iptal etti

        start_ch, end_ch, max_tokens = dlg.get_values()

        # NOT: _save_last_operation işlem bittikten sonra gerçek son bölümle çağrılır.
        # (Başlangıçta kaydedilirse, token limiti nedeniyle erken durulduğunda yanlış değer kalır.)

        self.thread = MLTerminologyWorker(project_path, start_chapter=start_ch,
                                          end_chapter=end_ch, max_tokens=max_tokens)
        self.thread.progress_update.connect(lambda msg: self.win.statusLabel.setText(f"Durum: {msg}"))
        self.thread.error_signal.connect(self._on_error)
        # finished_signal(int) → gerçekte işlenen son bölüm numarasını taşır
        self.thread.finished_signal.connect(
            lambda actual_end_ch: self._on_finished(project_path, start_ch, actual_end_ch)
        )

        self.win._set_ui_state_on_process_start(
            self.win.generateTerminologyButton, "Terminoloji Üretiliyor...",
            "#FFC107", "black", 0, "Durum: Terminoloji modeli çalışıyor, analiz ediliyor..."
        )
        self.win.progressBar.setMaximum(0)
        self.thread.start()

    def _save_last_operation(self, project_path: str, start_ch: int, end_ch: int):
        """Son terminoloji işleminin bölüm numaralarını proje config.ini'sine yazar."""
        import configparser
        config_path = os.path.join(project_path, "config", "config.ini")
        cfg = configparser.ConfigParser()
        try:
            if os.path.exists(config_path):
                cfg.read(config_path, encoding="utf-8")
            if "TerminologyOp" not in cfg:
                cfg["TerminologyOp"] = {}
            cfg["TerminologyOp"]["last_start_chapter"] = str(start_ch)
            cfg["TerminologyOp"]["last_end_chapter"] = str(end_ch)
            with open(config_path, "w", encoding="utf-8") as f:
                cfg.write(f)
        except Exception as e:
            from logger import app_logger
            app_logger.warning(f"Terminoloji bölüm bilgisi config.ini'ye yazılamadı: {e}")

    def _on_error(self, err):
        QMessageBox.critical(self.win, "Terminoloji Hatası", str(err))
        self.win._set_ui_state_on_process_end(
            self.win.generateTerminologyButton, "YZ İle Terminoloji Üret",
            "#E91E63", "white", f"Durum: Hata - {err}"
        )
        self.thread = None

    def _on_finished(self, project_path: str, start_ch: int, actual_end_ch: int):
        """İşlem bittiğinde gerçek son bölüm numarasıyla config.ini'yi günceller."""
        # Gerçekte işlenen son bölümü kaydet (kullanıcının girdiği değil)
        self._save_last_operation(project_path, start_ch, actual_end_ch)

        QMessageBox.information(self.win, "Başarılı",
                                f"Yapay Zeka ile terminoloji çıkarımı başarıyla tamamlandı.\n"
                                f"İşlenen bölümler: {start_ch} → {actual_end_ch}\n"
                                f"Sözlüğe yeni terimler eklendi.")
        self.win._set_ui_state_on_process_end(
            self.win.generateTerminologyButton, "YZ İle Terminoloji Üret",
            "#E91E63", "white", f"Durum: Hazır (Son bölüm: {actual_end_ch})"
        )
        self.thread = None

    def is_running(self):
        return self.thread is not None and self.thread.isRunning()

    def stop(self):
        pass  # MLTerminologyWorker QThread bazlı, doğrudan stop desteği yok
