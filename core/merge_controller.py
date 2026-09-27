"""
MergeController — Birleştirme işlemi iş mantığı kontrolcüsü.

Sorumluluklar:
  - Birleştirme thread/worker oluşturma ve yaşam döngüsü yönetimi
  - Seçili dosyaların toplanması ve sıralanması
"""

import os
from PyQt6.QtCore import Qt, QThread
from PyQt6.QtWidgets import QMessageBox

from core.workers.merging_worker import MergingWorker
from core.utils import natural_sort_key
from core.path_resolver import get_project_dir, get_subfolder_path


class MergeController:
    """Birleştirme işlemlerini yönetir."""

    def __init__(self, main_window):
        self.win = main_window
        self.thread = None
        self.worker = None

    def start(self):
        """Birleştirme işlemini başlatır."""
        current_item = self.win.project_list.currentItem()
        if not current_item:
            QMessageBox.warning(self.win, "Proje Seçilmedi", "Lütfen sol listeden bir proje seçin.")
            return

        project_name = current_item.text()
        project_path = get_project_dir(os.getcwd(), project_name)

        trslt_dir = get_subfolder_path(project_path, 'translate')
        selected_translated_file_paths = []
        for row in range(self.win.file_table.rowCount()):
            checkbox_item = self.win.file_table.item(row, 0)
            if checkbox_item and checkbox_item.checkState() == Qt.CheckState.Checked:
                translated_file_name = self.win.file_table.item(row, 2).text()
                if translated_file_name and translated_file_name != "Yok":
                    file_path = os.path.join(trslt_dir, translated_file_name)
                    if os.path.exists(file_path):
                        selected_translated_file_paths.append(file_path)

        if not selected_translated_file_paths:
            QMessageBox.warning(self.win, "Dosya Seçilmedi", "Lütfen birleştirmek için çevrilmiş dosya seçin.")
            return

        selected_translated_file_paths.sort(key=lambda x: natural_sort_key(os.path.basename(x)))
        self._stop_existing()

        output_merged_folder = get_subfolder_path(project_path, 'completed', create=True)

        self.thread = QThread()
        self.worker = MergingWorker(selected_translated_file_paths, output_merged_folder)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.progress.connect(self._on_progress)

        self.thread.start()

        self.win.translateButton.setEnabled(False)
        self.win.mergeButton.setEnabled(False)
        self.win.projectSettingsButton.setEnabled(False)
        self.win.token_count_button.setEnabled(False)
        self.win.mergeButton.setText("Birleştiriliyor...")
        self.win.mergeButton.setStyleSheet("background-color: #FFC107; color: black; border-radius: 5px; padding: 10px;")
        self.win.progressBar.setValue(0)
        self.win.progressBar.setMaximum(len(selected_translated_file_paths))
        self.win.progressBar.setVisible(True)
        self.win.statusLabel.setText(f"Durum: {len(selected_translated_file_paths)} dosya birleştiriliyor...")

    def _on_progress(self, current, total):
        self.win.progressBar.setValue(current)
        self.win.progressBar.setMaximum(total)
        self.win.statusLabel.setText(f"Durum: Birleştiriliyor... Dosya {current}/{total}")

    def _on_finished(self):
        QMessageBox.information(self.win, "Tamamlandı", "Seçili çevirileri birleştirme işlemi bitti.")
        self.win.translateButton.setEnabled(True)
        self.win.mergeButton.setEnabled(True)
        self.win.epubButton.setEnabled(True)
        self.win.projectSettingsButton.setEnabled(True)
        self.win.token_count_button.setEnabled(True)
        self.win.errorCheckButton.setEnabled(True)
        self.win.mergeButton.setText("Seçili Çevirileri Birleştir")
        self.win.mergeButton.setStyleSheet("background-color: #9C27B0; color: white; border-radius: 5px; padding: 10px;")
        self.win.progressBar.setVisible(False)
        self.win.statusLabel.setText("Durum: Hazır")
        self.thread = None
        self.worker = None
        self.win.sync_database_if_exists()
        self.win.update_file_list_from_selection()

    def _on_error(self, message):
        QMessageBox.critical(self.win, "Birleştirme Hatası", f"Bir hata oluştu:\n{message}")
        self.win.translateButton.setEnabled(True)
        self.win.mergeButton.setEnabled(True)
        self.win.epubButton.setEnabled(True)
        self.win.projectSettingsButton.setEnabled(True)
        self.win.token_count_button.setEnabled(True)
        self.win.errorCheckButton.setEnabled(True)
        self.win.mergeButton.setText("Seçili Çevirileri Birleştir")
        self.win.mergeButton.setStyleSheet("background-color: #FF5722; color: white; border-radius: 5px; padding: 10px;")
        self.win.progressBar.setVisible(False)
        self.win.statusLabel.setText(f"Durum: Hata - {message}")
        self.win.progressBar.setVisible(False)
        self.win.statusLabel.setText(f"Durum: Hata - {message}")
        self.thread = None
        self.worker = None
        self.win.update_file_list_from_selection()

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
