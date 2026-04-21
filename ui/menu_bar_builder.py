"""
MenuBarBuilder — Ana pencere menü barı oluşturucu.

Sorumluluklar:
  - Menü barı yapısını oluşturma
  - Menü aksiyonlarını bağlama
  - JS dosya kaydetme işlemi
"""

import os
import shutil
from PyQt6.QtWidgets import QMessageBox, QFileDialog


def build_menu_bar(main_window):
    """Ana pencere menü barını oluşturur ve aksiyonları bağlar."""
    win = main_window
    menu_bar = win.menuBar()

    # ── Dosya Menüsü ──
    file_menu = menu_bar.addMenu("Dosya")
    new_project_action = file_menu.addAction("Yeni Proje")
    new_project_action.triggered.connect(win.new_project_clicked)
    save_action = file_menu.addAction("Ayarları Kaydet")
    save_action.triggered.connect(win.open_project_settings_dialog)
    exit_action = file_menu.addAction("Çıkış")
    exit_action.triggered.connect(win.close)

    # ── Proje Menüsü ──
    project_menu = menu_bar.addMenu("Proje")
    delete_project_action = project_menu.addAction("Proje Sil")
    delete_project_action.triggered.connect(win.delete_project_clicked)
    project_settings_action = project_menu.addAction("Proje Ayarları")
    project_settings_action.triggered.connect(win.open_project_settings_dialog)

    # ── Ayarlar Menüsü ──
    settings_menu = menu_bar.addMenu("Ayarlar")
    prompt_editor_action = settings_menu.addAction("Promt Editörü")
    prompt_editor_action.triggered.connect(win.open_prompt_editor)
    apikey_editor_action = settings_menu.addAction("API Key Editörü")
    apikey_editor_action.triggered.connect(win.open_apikey_editor)
    gemini_version_action = settings_menu.addAction("Gemini Versiyon")
    gemini_version_action.triggered.connect(win.open_gemini_version_dialog)
    mcp_action = settings_menu.addAction("Yapay Zeka Kaynağı (MCP)")
    mcp_action.triggered.connect(win.open_mcp_dialog)
    settings_menu.addSeparator()
    theme_manager_action = settings_menu.addAction("🎨 Tema Yöneticisi")
    theme_manager_action.triggered.connect(win.open_theme_manager_dialog)
    app_settings_action = settings_menu.addAction("⚙️ Uygulama Ayarları")
    app_settings_action.triggered.connect(win.open_app_settings_dialog)

    # ── JS Kaydet Menüsü ──
    js_save_menu = menu_bar.addMenu("JS Kaydet")
    save_booktoki_action = js_save_menu.addAction("Booktoki")
    save_booktoki_action.triggered.connect(lambda: _save_js_file(win, "booktoki.js"))
    save_69shuba_action = js_save_menu.addAction("69shuba")
    save_69shuba_action.triggered.connect(lambda: _save_js_file(win, "69shuba.js"))
    save_novelfire_action = js_save_menu.addAction("Novelfire")
    save_novelfire_action.triggered.connect(lambda: _save_js_file(win, "novelfire.js"))

    # ── JSON Kaydet Menüsü ──
    json_save_action = menu_bar.addAction("JSON Kaydet")
    json_save_action.triggered.connect(lambda: _run_json_output(win))

    # ── Yardım Menüsü ──
    help_menu = menu_bar.addMenu("Yardım")
    about_action = help_menu.addAction("Hakkında")
    about_action.triggered.connect(win.show_about_dialog)
    api_stats_action = help_menu.addAction("📊 API Kullanım İstatistikleri")
    api_stats_action.triggered.connect(win.show_api_stats_dialog)


def _save_js_file(main_window, js_filename):
    """Kullanıcının seçtiği JS dosyasını istediği yere kaydetmesini sağlar."""
    source_path = os.path.join(os.getcwd(), js_filename)

    if not os.path.exists(source_path):
        try:
            from core.js_create import create_js_file
            create_js_file(js_filename)
        except Exception:
            pass

    if not os.path.exists(source_path):
        QMessageBox.warning(main_window, "Dosya Bulunamadı", f"'{js_filename}' dosyası ana dizinde bulunamadı!")
        return

    default_save_path = os.path.join(os.path.expanduser("~"), "Desktop", js_filename)
    save_path, _ = QFileDialog.getSaveFileName(
        main_window, f"{js_filename} Dosyasını Kaydet", default_save_path,
        "JavaScript Files (*.js);;All Files (*)"
    )

    if save_path:
        try:
            shutil.copy2(source_path, save_path)
            QMessageBox.information(main_window, "Başarılı", f"Dosya başarıyla kaydedildi:\n{save_path}")
        except Exception as e:
            QMessageBox.critical(main_window, "Kayıt Hatası", f"Dosya kaydedilirken bir hata oluştu:\n{str(e)}")


def _run_json_output(win):
    """Seçili çeviri dosyalarını okuyarak bir JSON dosyasına aktarır."""
    from core.workers.jsonoutput import JsonOutputWorker
    from core.utils import natural_sort_key
    from PyQt6.QtCore import Qt
    
    current_item = win.project_list.currentItem()
    if not current_item:
        QMessageBox.warning(win, "Proje Seçilmedi", "Lütfen sol listeden bir proje seçin.")
        return
        
    project_name = current_item.text()
    project_path = os.path.join(os.getcwd(), project_name)

    selected_files = []
    # QTableWidget üzerinden işaretli satırların 'Çevrilen Dosya' kolonunu(Index 2) alın
    for row in range(win.file_table.rowCount()):
        checkbox_item = win.file_table.item(row, 0)
        if checkbox_item and checkbox_item.checkState() == Qt.CheckState.Checked:
            translated_file_name = win.file_table.item(row, 2).text()
            if translated_file_name and translated_file_name != "Yok":
                file_path = os.path.join(project_path, 'trslt', translated_file_name)
                if os.path.exists(file_path):
                    selected_files.append(file_path)

    if not selected_files:
        QMessageBox.warning(win, "Dosya Seçilmedi", "Lütfen işlenecek çevrilmiş dosya seçin.")
        return
        
    selected_files.sort(key=lambda x: natural_sort_key(os.path.basename(x)))
    
    if hasattr(win, 'json_worker') and win.json_worker.isRunning():
        QMessageBox.warning(win, "Devam Eden İşlem", "Şu anda zaten çalışan bir JSON kayıt işlemi var.")
        return
        
    win.json_worker = JsonOutputWorker(selected_files, project_path, project_name)
    win.json_worker.error.connect(lambda msg: QMessageBox.critical(win, "Hata", msg))
    win.json_worker.success.connect(lambda msg: QMessageBox.information(win, "Başarılı", msg))
    win.json_worker.start()
