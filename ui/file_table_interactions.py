"""
FileTableInteractions — Dosya tablosu etkileşimleri.

Sorumluluklar:
  - Sağ tıklama menüsü, çift tıklama, önizleme
  - Dosya/klasör açma, satır seçimi, arama filtreleme
"""

import os
import sys
import subprocess
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMenu, QMessageBox, QTableWidget

from ui.text_editor_dialog import TextEditorDialog
from ui.file_preview_dialog import FilePreviewDialog
from core.localization import tr


class FileTableInteractions:
    def __init__(self, main_window):
        self.win = main_window

    def setup(self):
        """Tablo etkileşimlerini bağlar."""
        win = self.win
        win.file_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        win.file_table.customContextMenuRequested.connect(self.context_menu)
        win.file_table.cellDoubleClicked.connect(self.on_double_click)
        win.file_table.keyPressEvent = self.table_key_press_event

    def context_menu(self, position):
        index = self.win.file_table.indexAt(position)
        if not index.isValid():
            return
        row = index.row()
        column = index.column()
        menu = QMenu(self.win)
        preview_action = QAction(tr("file_table.action_preview", "📄 Hızlı Önizleme"), self.win)
        preview_action.triggered.connect(self.show_file_preview)
        menu.addAction(preview_action)
        menu.addSeparator()
        open_file_action = QAction(tr("file_table.action_open_file", "Dosyayı Aç"), self.win)
        open_file_action.triggered.connect(lambda: self.open_selected_file(row, column))
        menu.addAction(open_file_action)
        open_folder_action = QAction(tr("file_table.action_open_folder", "Klasörü Aç"), self.win)
        open_folder_action.triggered.connect(lambda: self.open_selected_folder(row, column))
        menu.addAction(open_folder_action)
        menu.exec(self.win.file_table.viewport().mapToGlobal(position))

    def on_double_click(self, row, column):
        if not self.win.current_project_path:
            return
        if column not in (1, 2):
            return
        item = self.win.file_table.item(row, column)
        if not item:
            return
        file_name = item.text()
        if file_name in ("Yok", "Orijinali Yok", "N/A", tr("file_table.none", "Yok"), tr("file_table.status_no_original", "Orijinali Yok")):
            return
        if column == 1:
            file_path = os.path.join(self.win.current_project_path, 'dwnld', file_name)
        else:
            status = self.win.file_table.item(row, 5).text() if self.win.file_table.item(row, 5) else ""
            if "Birleştirildi" in status or tr("file_table.status_merged", "Birleştirildi") in status:
                file_path = os.path.join(self.win.current_project_path, 'cmplt', file_name)
            else:
                file_path = os.path.join(self.win.current_project_path, 'trslt', file_name)
        if os.path.exists(file_path):
            editor = TextEditorDialog(file_path, self.win, project_path=self.win.current_project_path)
            editor.exec()
        else:
            QMessageBox.warning(self.win, tr("menu_bar.msg_file_not_found_title", "Dosya Bulunamadı"), tr("file_table.msg_file_not_found_body", "Dosya bulunamadı:\n{}").format(file_path))

    def table_key_press_event(self, event):
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            self.mark_highlighted_rows_checked()
        else:
            QTableWidget.keyPressEvent(self.win.file_table, event)

    def mark_highlighted_rows_checked(self):
        selected_rows = set()
        for item in self.win.file_table.selectedItems():
            selected_rows.add(item.row())
        for row in selected_rows:
            checkbox_item = self.win.file_table.item(row, 0)
            if checkbox_item:
                checkbox_item.setCheckState(Qt.CheckState.Checked)

    def show_file_preview(self):
        row = self.win.file_table.currentRow()
        if row < 0:
            return
        current_item = self.win.project_list.currentItem()
        if not current_item:
            return
        project_name = current_item.text()
        project_path = os.path.join(os.getcwd(), project_name)
        translated_item = self.win.file_table.item(row, 2)
        original_item = self.win.file_table.item(row, 1)
        file_to_preview = None
        if translated_item and translated_item.text() not in ("", "Yok", "Orijinali Yok", tr("file_table.none", "Yok"), tr("file_table.status_no_original", "Orijinali Yok")):
            candidate = os.path.join(project_path, "trslt", translated_item.text())
            if os.path.exists(candidate):
                file_to_preview = candidate
        if not file_to_preview and original_item and original_item.text() not in ("", "Orijinali Yok", tr("file_table.status_no_original", "Orijinali Yok")):
            candidate = os.path.join(project_path, "dwnld", original_item.text())
            if os.path.exists(candidate):
                file_to_preview = candidate
        if not file_to_preview:
            QMessageBox.warning(self.win, tr("menu_bar.msg_file_not_found_title", "Dosya Bulunamadı"), tr("file_table.msg_no_previewable_file", "Seçili satırda gösterilebilecek bir dosya bulunamadı."))
            return
        preview = FilePreviewDialog(file_to_preview, parent=self.win, project_path=project_path)
        preview.exec()

    def open_selected_file(self, row, clicked_column):
        if not self.win.current_project_path:
            QMessageBox.warning(self.win, tr("main_window.msg_structure_error_title", "Hata"), tr("menu_bar.msg_json_project_not_selected_body", "Lütfen önce bir proje seçin."))
            return
        original_file_name = self.win.file_table.item(row, 1).text()
        translated_file_name = self.win.file_table.item(row, 2).text()
        status = self.win.file_table.item(row, 5).text()
        file_path_to_open = self._resolve_file_path(
            clicked_column, original_file_name, translated_file_name, status
        )
        if file_path_to_open and os.path.exists(file_path_to_open):
            self._open_path(file_path_to_open)
        else:
            QMessageBox.warning(self.win, tr("menu_bar.msg_file_not_found_title", "Dosya Bulunamadı"), tr("file_table.msg_file_not_found_generic", "Seçilen dosyanın yolu mevcut değil veya dosya bulunamadı."))

    def open_selected_folder(self, row, clicked_column):
        if not self.win.current_project_path:
            QMessageBox.warning(self.win, tr("main_window.msg_structure_error_title", "Hata"), tr("menu_bar.msg_json_project_not_selected_body", "Lütfen önce bir proje seçin."))
            return
        original_file_name = self.win.file_table.item(row, 1).text()
        translated_file_name = self.win.file_table.item(row, 2).text()
        status = self.win.file_table.item(row, 5).text()
        folder_path = self._resolve_folder_path(
            clicked_column, original_file_name, translated_file_name, status
        )
        if folder_path and os.path.exists(folder_path):
            self._open_path(folder_path)
        else:
            QMessageBox.warning(self.win, tr("file_table.msg_folder_not_found_title", "Klasör Bulunamadı"), tr("file_table.msg_folder_not_found_body", "Seçilen dosyanın klasör yolu mevcut değil veya klasör bulunamadı."))

    def _resolve_file_path(self, col, orig, trans, status):
        pp = self.win.current_project_path
        status_merged = tr("file_table.status_merged", "Birleştirildi")
        status_untranslated = tr("file_table.status_no_original_untranslated", "Orijinali Yok, Çevrilmedi")
        status_downloaded = tr("file_table.status_downloaded", "İndirildi")
        
        if col == 1 or col == 6:
            if orig and orig != "Orijinali Yok" and orig != "N/A" and orig != tr("file_table.status_no_original", "Orijinali Yok"):
                return os.path.join(pp, 'dwnld', orig)
        elif col == 2 or col == 7:
            if (status == "Birleştirildi" or status == status_merged) and trans and trans != "Yok" and trans != tr("file_table.none", "Yok"):
                return os.path.join(pp, 'cmplt', trans)
            elif trans and trans != "Yok" and trans != tr("file_table.none", "Yok"):
                return os.path.join(pp, 'trslt', trans)
        else:
            if (status == "Birleştirildi" or status == status_merged) and trans and trans != "Yok" and trans != tr("file_table.none", "Yok"):
                return os.path.join(pp, 'cmplt', trans)
            elif trans and trans != "Yok" and trans != tr("file_table.none", "Yok") and (
                "Çevrildi" in status or tr("file_table.status_translated", "Çevrildi") in status or
                status.startswith("Hata:") or status.startswith(tr("file_table.status_error_prefix", "Hata:")) or
                "Temizlenmedi" in status or "Temizlendi" in status
            ):
                return os.path.join(pp, 'trslt', trans)
            elif orig and orig != "Orijinali Yok" and orig != tr("file_table.status_no_original", "Orijinali Yok") and (
                "İndirildi" in status or status == status_downloaded or
                status.startswith("Hata:") or status.startswith(tr("file_table.status_error_prefix", "Hata:"))
            ):
                return os.path.join(pp, 'dwnld', orig)
        return None

    def _resolve_folder_path(self, col, orig, trans, status):
        pp = self.win.current_project_path
        status_merged = tr("file_table.status_merged", "Birleştirildi")
        status_downloaded = tr("file_table.status_downloaded", "İndirildi")
        
        if col == 1 or col == 6:
            if orig and orig != "Orijinali Yok" and orig != "N/A" and orig != tr("file_table.status_no_original", "Orijinali Yok"):
                return os.path.join(pp, 'dwnld')
        elif col == 2 or col == 7:
            if (status == "Birleştirildi" or status == status_merged) and trans and trans != "Yok" and trans != tr("file_table.none", "Yok"):
                return os.path.join(pp, 'cmplt')
            elif trans and trans != "Yok" and trans != tr("file_table.none", "Yok"):
                return os.path.join(pp, 'trslt')
        else:
            if (status == "Birleştirildi" or status == status_merged) and trans and trans != "Yok" and trans != tr("file_table.none", "Yok"):
                return os.path.join(pp, 'cmplt')
            elif trans and trans != "Yok" and trans != tr("file_table.none", "Yok") and (
                "Çevrildi" in status or tr("file_table.status_translated", "Çevrildi") in status or
                status.startswith("Hata:") or status.startswith(tr("file_table.status_error_prefix", "Hata:"))
            ):
                return os.path.join(pp, 'trslt')
            elif orig and orig != "Orijinali Yok" and orig != tr("file_table.status_no_original", "Orijinali Yok") and (
                "İndirildi" in status or status == status_downloaded or
                status.startswith("Hata:") or status.startswith(tr("file_table.status_error_prefix", "Hata:"))
            ):
                return os.path.join(pp, 'dwnld')
        return None

    def _open_path(self, path):
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.run(["open", path])
            else:
                subprocess.run(["xdg-open", path])
        except Exception as e:
            QMessageBox.critical(self.win, tr("file_table.msg_open_error_title", "Açma Hatası"), tr("file_table.msg_open_error_body", "Açılamadı:\n{}").format(e))

    def filter_project_list(self, text):
        search = text.lower()
        for i in range(self.win.project_list.count()):
            item = self.win.project_list.item(i)
            item.setHidden(search not in item.text().lower() if search else False)

    def filter_file_table(self, text):
        search = text.lower()
        for row in range(self.win.file_table.rowCount()):
            match = False
            for col in range(1, 3):
                item = self.win.file_table.item(row, col)
                if item and search in item.text().lower():
                    match = True
                    break
            self.win.file_table.setRowHidden(row, not match if search else False)
