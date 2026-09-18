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
from core.path_resolver import get_subfolder_path


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
        menu.addSeparator()

        orig_item = self.win.file_table.item(row, 1)
        trans_item = self.win.file_table.item(row, 2)
        status_item = self.win.file_table.item(row, 3)

        original_file_name = orig_item.text() if orig_item else ""
        translated_file_name = trans_item.text() if trans_item else ""
        status = status_item.text() if status_item else ""

        has_orig = bool(original_file_name and original_file_name not in ("Orijinali Yok", "N/A", "", tr("file_table.status_no_original", "Orijinali Yok")))
        has_trans = bool(translated_file_name and translated_file_name not in ("Yok", "", tr("file_table.none", "Yok")))
        is_merged = "Birleştirildi" in status or tr("file_table.status_merged", "Birleştirildi") in status or original_file_name == "N/A"

        if is_merged:
            del_lbl = tr("file_table.action_delete_merged", "🗑️ Birleştirilmiş/EPUB Dosyasını Sil")
            del_action = QAction(f"{del_lbl} ({translated_file_name})", self.win)
            del_action.triggered.connect(lambda: self.delete_file_entry(row, target="completed"))
            menu.addAction(del_action)
        else:
            if has_orig and has_trans:
                if column == 1:
                    del_orig = QAction(tr("file_table.action_delete_orig", f"🗑️ Orijinal Dosyayı Sil ({original_file_name})"), self.win)
                    del_orig.triggered.connect(lambda: self.delete_file_entry(row, target="original"))
                    menu.addAction(del_orig)

                    del_trans = QAction(tr("file_table.action_delete_trans", f"🗑️ Çevrilmiş Dosyayı Sil ({translated_file_name})"), self.win)
                    del_trans.triggered.connect(lambda: self.delete_file_entry(row, target="translated"))
                    menu.addAction(del_trans)
                elif column == 2:
                    del_trans = QAction(tr("file_table.action_delete_trans", f"🗑️ Çevrilmiş Dosyayı Sil ({translated_file_name})"), self.win)
                    del_trans.triggered.connect(lambda: self.delete_file_entry(row, target="translated"))
                    menu.addAction(del_trans)

                    del_orig = QAction(tr("file_table.action_delete_orig", f"🗑️ Orijinal Dosyayı Sil ({original_file_name})"), self.win)
                    del_orig.triggered.connect(lambda: self.delete_file_entry(row, target="original"))
                    menu.addAction(del_orig)
                else:
                    del_orig = QAction(tr("file_table.action_delete_orig", f"🗑️ Orijinal Dosyayı Sil ({original_file_name})"), self.win)
                    del_orig.triggered.connect(lambda: self.delete_file_entry(row, target="original"))
                    menu.addAction(del_orig)

                    del_trans = QAction(tr("file_table.action_delete_trans", f"🗑️ Çevrilmiş Dosyayı Sil ({translated_file_name})"), self.win)
                    del_trans.triggered.connect(lambda: self.delete_file_entry(row, target="translated"))
                    menu.addAction(del_trans)

                del_both = QAction(tr("file_table.action_delete_both", "🗑️ Her İkisini de Sil"), self.win)
                del_both.triggered.connect(lambda: self.delete_file_entry(row, target="both"))
                menu.addAction(del_both)
            elif has_orig:
                del_orig = QAction(tr("file_table.action_delete_orig", f"🗑️ Orijinal Dosyayı Sil ({original_file_name})"), self.win)
                del_orig.triggered.connect(lambda: self.delete_file_entry(row, target="original"))
                menu.addAction(del_orig)
            elif has_trans:
                del_trans = QAction(tr("file_table.action_delete_trans", f"🗑️ Çevrilmiş Dosyayı Sil ({translated_file_name})"), self.win)
                del_trans.triggered.connect(lambda: self.delete_file_entry(row, target="translated"))
                menu.addAction(del_trans)
            else:
                del_gen = QAction(tr("file_table.action_delete_file", "🗑️ Dosyayı Sil"), self.win)
                del_gen.triggered.connect(lambda: self.delete_file_entry(row, target="both"))
                menu.addAction(del_gen)

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
            file_path = os.path.join(get_subfolder_path(self.win.current_project_path, 'download'), file_name)
        else:
            status = self.win.file_table.item(row, 3).text() if self.win.file_table.item(row, 3) else ""
            if "Birleştirildi" in status or tr("file_table.status_merged", "Birleştirildi") in status:
                file_path = os.path.join(get_subfolder_path(self.win.current_project_path, 'completed'), file_name)
            else:
                file_path = os.path.join(get_subfolder_path(self.win.current_project_path, 'translate'), file_name)
        if os.path.exists(file_path):
            if hasattr(self.win, 'goto_text_editor_page'):
                self.win.goto_text_editor_page(file_path=file_path)
            else:
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
            candidate = os.path.join(get_subfolder_path(project_path, 'translate'), translated_item.text())
            if os.path.exists(candidate):
                file_to_preview = candidate
        if not file_to_preview and original_item and original_item.text() not in ("", "Orijinali Yok", tr("file_table.status_no_original", "Orijinali Yok")):
            candidate = os.path.join(get_subfolder_path(project_path, 'download'), original_item.text())
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
        orig_item = self.win.file_table.item(row, 1)
        trans_item = self.win.file_table.item(row, 2)
        status_item = self.win.file_table.item(row, 3)
        original_file_name = orig_item.text() if orig_item else ""
        translated_file_name = trans_item.text() if trans_item else ""
        status = status_item.text() if status_item else ""
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
        orig_item = self.win.file_table.item(row, 1)
        trans_item = self.win.file_table.item(row, 2)
        status_item = self.win.file_table.item(row, 3)
        original_file_name = orig_item.text() if orig_item else ""
        translated_file_name = trans_item.text() if trans_item else ""
        status = status_item.text() if status_item else ""
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
        status_downloaded = tr("file_table.status_downloaded", "İndirildi")
        is_merged = "Birleştirildi" in status or status_merged in status
        
        if col == 1 or col == 6:
            if orig and orig not in ("Orijinali Yok", "N/A", tr("file_table.status_no_original", "Orijinali Yok")):
                return os.path.join(get_subfolder_path(pp, "download"), orig)
        elif col == 2 or col == 7:
            if is_merged and trans and trans not in ("Yok", tr("file_table.none", "Yok")):
                candidate = os.path.join(get_subfolder_path(pp, "completed"), trans)
                if os.path.exists(candidate):
                    return candidate
                return os.path.join(get_subfolder_path(pp, "translate"), trans)
            elif trans and trans not in ("Yok", tr("file_table.none", "Yok")):
                return os.path.join(get_subfolder_path(pp, "translate"), trans)
        else:
            if is_merged and trans and trans not in ("Yok", tr("file_table.none", "Yok")):
                candidate = os.path.join(get_subfolder_path(pp, "completed"), trans)
                if os.path.exists(candidate):
                    return candidate
                return os.path.join(get_subfolder_path(pp, "translate"), trans)
            elif trans and trans not in ("Yok", tr("file_table.none", "Yok")):
                return os.path.join(get_subfolder_path(pp, "translate"), trans)
            elif orig and orig not in ("Orijinali Yok", tr("file_table.status_no_original", "Orijinali Yok")):
                return os.path.join(get_subfolder_path(pp, "download"), orig)
        return None

    def _resolve_folder_path(self, col, orig, trans, status):
        pp = self.win.current_project_path
        status_merged = tr("file_table.status_merged", "Birleştirildi")
        status_downloaded = tr("file_table.status_downloaded", "İndirildi")
        is_merged = "Birleştirildi" in status or status_merged in status
        
        if col == 1 or col == 6:
            if orig and orig not in ("Orijinali Yok", "N/A", tr("file_table.status_no_original", "Orijinali Yok")):
                return get_subfolder_path(pp, "download")

        if is_merged and trans and trans not in ("Yok", tr("file_table.none", "Yok")):
            candidate = get_subfolder_path(pp, "completed")
            if os.path.exists(candidate):
                return candidate
            return get_subfolder_path(pp, "translate")
        elif trans and trans not in ("Yok", tr("file_table.none", "Yok")):
            return get_subfolder_path(pp, "translate")
        elif orig and orig not in ("Orijinali Yok", tr("file_table.status_no_original", "Orijinali Yok")):
            return get_subfolder_path(pp, "download")

        return None

    def delete_selected_file(self, row):
        """Varsayılan olarak seçili satırdaki tüm dosyaları siler (geriye dönük uyumluluk)."""
        self.delete_file_entry(row, target="both")

    def delete_file_entry(self, row, target="both"):
        """
        Seçili satırdaki hedeflenen dosyayı (orijinal, çevrilmiş, her ikisi veya birleştirilmiş) 
        kullanıcı onayından sonra diskten ve veritabanından siler, tabloyu/UI'ı yeniler.
        target: 'original', 'translated', 'both', 'completed'
        """
        if not self.win.current_project_path:
            QMessageBox.warning(self.win, tr("main_window.msg_structure_error_title", "Hata"),
                                tr("menu_bar.msg_json_project_not_selected_body", "Lütfen önce bir proje seçin."))
            return

        pp = self.win.current_project_path
        orig_item = self.win.file_table.item(row, 1)
        trans_item = self.win.file_table.item(row, 2)
        status_item = self.win.file_table.item(row, 3)

        original_file_name = orig_item.text() if orig_item else ""
        translated_file_name = trans_item.text() if trans_item else ""
        status = status_item.text() if status_item else ""

        has_orig = bool(original_file_name and original_file_name not in ("Orijinali Yok", "N/A", "", tr("file_table.status_no_original", "Orijinali Yok")))
        has_trans = bool(translated_file_name and translated_file_name not in ("Yok", "", tr("file_table.none", "Yok")))
        is_merged = target == "completed" or "Birleştirildi" in status or tr("file_table.status_merged", "Birleştirildi") in status or original_file_name == "N/A"

        # Onay mesajı metni
        if target == "original":
            confirm_msg = tr("file_table.delete_confirm_orig", f"Yalnızca orijinal dosyayı ({original_file_name}) silmek istediğinize emin misiniz?")
        elif target == "translated":
            confirm_msg = tr("file_table.delete_confirm_trans", f"Yalnızca çevrilmiş dosyayı ({translated_file_name}) silmek istediğinize emin misiniz?")
        elif is_merged or target == "completed":
            confirm_msg = tr("file_table.delete_confirm_merged", f"Birleştirilmiş/EPUB dosyasını ({translated_file_name}) silmek istediğinize emin misiniz?")
        else:
            display_name = original_file_name or translated_file_name or f"Satır {row + 1}"
            confirm_msg = tr("file_table.delete_confirm_both", f"Seçili tüm dosyaları silmek istediğinize emin misiniz?\n\n{display_name}")

        reply = QMessageBox.question(
            self.win,
            tr("file_table.delete_confirm_title", "Dosyayı Sil"),
            confirm_msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        from core.database_manager import DatabaseManager
        db_mgr = DatabaseManager(pp)
        db_entries = db_mgr.get_all_files() if db_mgr.db_exists() else []

        target_db_entry = None
        for entry in db_entries:
            if has_orig and entry.get("original_file_name") == original_file_name:
                target_db_entry = entry
                break
            if has_trans and entry.get("translated_file_name") == translated_file_name:
                target_db_entry = entry
                break

        if target_db_entry:
            sort_key = target_db_entry["sort_key"]
        elif is_merged:
            sort_key = f"merged_{translated_file_name.replace('.txt', '').replace('.json', '').replace('.epub', '')}"
        elif has_orig:
            sort_key = original_file_name.replace(".txt", "")
        else:
            sort_key = translated_file_name.replace("translated_", "").replace(".txt", "")

        download_folder = get_subfolder_path(pp, 'download')
        translate_folder = get_subfolder_path(pp, 'translate')
        completed_folder = get_subfolder_path(pp, 'completed')

        if is_merged or target == "completed":
            if translated_file_name and translated_file_name not in ("Yok", ""):
                cmplt_path = os.path.join(completed_folder, translated_file_name)
                if os.path.exists(cmplt_path):
                    try:
                        os.remove(cmplt_path)
                    except Exception as e:
                        QMessageBox.warning(self.win, tr("file_table.delete_error_title", "Silme Hatası"),
                                            tr("file_table.delete_error_body", f"Dosya silinemedi:\n{e}"))
            db_mgr.delete_file(sort_key)

        elif target == "original":
            if has_orig:
                orig_path = os.path.join(download_folder, original_file_name)
                if os.path.exists(orig_path):
                    try:
                        os.remove(orig_path)
                    except Exception as e:
                        QMessageBox.warning(self.win, tr("file_table.delete_error_title", "Silme Hatası"),
                                            tr("file_table.delete_error_body", f"Orijinal dosya silinemedi:\n{e}"))

            if has_trans:
                if target_db_entry:
                    updated_entry = dict(target_db_entry)
                    updated_entry["original_file_name"] = "Orijinali Yok"
                    updated_entry["original_file_path"] = ""
                    updated_entry["display_status"] = f"Orijinali Yok, {updated_entry.get('translation_status', 'Çevrildi')}"
                    db_mgr.upsert_single_file(updated_entry)
                else:
                    db_mgr.upsert_single_file({
                        "sort_key": sort_key,
                        "original_file_name": "Orijinali Yok",
                        "original_file_path": "",
                        "translated_file_name": translated_file_name,
                        "translated_file_path": os.path.join(translate_folder, translated_file_name),
                        "translation_status": "Çevrildi",
                        "is_translated": True,
                        "display_status": "Orijinali Yok, Çevrildi"
                    })
            else:
                db_mgr.delete_file(sort_key)

        elif target == "translated":
            if has_trans:
                trans_path = os.path.join(translate_folder, translated_file_name)
                cmplt_path = os.path.join(completed_folder, translated_file_name)
                if os.path.exists(trans_path):
                    try:
                        os.remove(trans_path)
                    except Exception as e:
                        QMessageBox.warning(self.win, tr("file_table.delete_error_title", "Silme Hatası"),
                                            tr("file_table.delete_error_body", f"Çevrilmiş dosya silinemedi:\n{e}"))
                elif os.path.exists(cmplt_path):
                    try:
                        os.remove(cmplt_path)
                    except Exception as e:
                        QMessageBox.warning(self.win, tr("file_table.delete_error_title", "Silme Hatası"),
                                            tr("file_table.delete_error_body", f"Çevrilmiş dosya silinemedi:\n{e}"))

            if has_orig:
                if target_db_entry:
                    updated_entry = dict(target_db_entry)
                    updated_entry["translated_file_name"] = ""
                    updated_entry["translated_file_path"] = ""
                    updated_entry["translation_status"] = "Çevrilmedi"
                    updated_entry["is_translated"] = False
                    updated_entry["display_status"] = "İndirildi"
                    db_mgr.upsert_single_file(updated_entry)
                else:
                    db_mgr.upsert_single_file({
                        "sort_key": sort_key,
                        "original_file_name": original_file_name,
                        "original_file_path": os.path.join(download_folder, original_file_name),
                        "translated_file_name": "",
                        "translated_file_path": "",
                        "translation_status": "Çevrilmedi",
                        "is_translated": False,
                        "display_status": "İndirildi"
                    })
            else:
                db_mgr.delete_file(sort_key)

        else: # target == "both"
            if has_orig:
                orig_path = os.path.join(download_folder, original_file_name)
                if os.path.exists(orig_path):
                    try:
                        os.remove(orig_path)
                    except Exception:
                        pass
            if has_trans:
                trans_path = os.path.join(translate_folder, translated_file_name)
                cmplt_path = os.path.join(completed_folder, translated_file_name)
                if os.path.exists(trans_path):
                    try:
                        os.remove(trans_path)
                    except Exception:
                        pass
                elif os.path.exists(cmplt_path):
                    try:
                        os.remove(cmplt_path)
                    except Exception:
                        pass

            db_mgr.delete_file(sort_key)

        if hasattr(self.win, "update_file_list_from_selection"):
            self.win.update_file_list_from_selection()
        else:
            self.win.file_table.removeRow(row)

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
