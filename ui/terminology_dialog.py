import sys
import os
import configparser
from PyQt6.QtWidgets import (
    QDialog, QLineEdit, QFormLayout, QDialogButtonBox, 
    QMessageBox, QLabel, QApplication, QTextEdit, QListWidget, 
    QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QInputDialog,
    QSpinBox, QCheckBox, QGroupBox, QSplitter, QWidget, QProgressBar
)
from PyQt6.QtGui import QIntValidator, QFont, QIcon, QAction
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject, QSize
from logger import app_logger
from core.localization import tr

# ─── V2.1.0 Geriye Uyumluluk Re-export'lar ───
# ui/ paketine taşınan sınıflar burada da erişilebilir kalır.
# Eski "from dialogs import X" çağrıları kırılmaz.
try:
    from ui.app_settings_dialog import AppSettingsDialog
    from ui.file_preview_dialog import FilePreviewDialog
except ImportError:
    pass  # ui paketi henüz mevcut değilse sessizce geç



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
                # Item text: Dosya Adı, Item Data: Dosya İçeriği
                combobox.addItem(f.replace('.txt', ''), content)
            except:
                pass


class TerminologyDialog(QDialog):
    """Proje bazlı terminoloji/terim sözlüğü yönetim paneli."""

    def __init__(self, project_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("terminology.window_title", "Terminoloji Sözlüğü"))
        self.resize(650, 500)
        self.project_path = project_path

        from terminology.terminology_manager import TerminologyManager
        self.manager = TerminologyManager(project_path)

        layout = QVBoxLayout(self)

        # Tablo
        from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels([tr("terminology.header_source", "Kaynak Terim"), tr("terminology.header_target", "Hedef Terim"), tr("terminology.header_note", "Not")])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        # Yeni terim ekleme
        add_group = QGroupBox(tr("terminology.add_group", "Yeni Terim Ekle"))
        add_layout = QHBoxLayout()
        self.source_input = QLineEdit()
        self.source_input.setPlaceholderText(tr("terminology.placeholder_source", "Kaynak (ör: 黑暗之王)"))
        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText(tr("terminology.placeholder_target", "Hedef (ör: Karanlık Kral)"))
        self.note_input = QLineEdit()
        self.note_input.setPlaceholderText(tr("terminology.placeholder_note", "Not (opsiyonel)"))

        add_btn = QPushButton(tr("terminology.btn_add", "➕ Ekle"))
        add_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        add_btn.clicked.connect(self.add_term)

        add_layout.addWidget(self.source_input)
        add_layout.addWidget(self.target_input)
        add_layout.addWidget(self.note_input)
        add_layout.addWidget(add_btn)
        add_group.setLayout(add_layout)
        layout.addWidget(add_group)

        # Butonlar
        btn_layout = QHBoxLayout()

        del_btn = QPushButton(tr("terminology.btn_delete_selected", "🗑️ Seçileni Sil"))
        del_btn.setStyleSheet("color: red;")
        del_btn.clicked.connect(self.delete_term)

        import_btn = QPushButton(tr("terminology.btn_import", "📥 İçe Aktar"))
        import_btn.clicked.connect(self.import_terms)

        export_btn = QPushButton(tr("terminology.btn_export", "📤 Dışa Aktar"))
        export_btn.clicked.connect(self.export_terms)

        clear_btn = QPushButton(tr("terminology.btn_clear_all", "🧹 Tümünü Temizle"))
        clear_btn.clicked.connect(self.clear_terms)

        btn_layout.addWidget(del_btn)
        btn_layout.addWidget(import_btn)
        btn_layout.addWidget(export_btn)
        btn_layout.addWidget(clear_btn)

        self.generate_btn = QPushButton(tr("terminology.btn_generate", "⚡ Sıfırdan Üret"))
        self.generate_btn.setStyleSheet("background-color: #E91E63; color: white;")
        self.generate_btn.clicked.connect(self.generate_from_scratch)
        btn_layout.addWidget(self.generate_btn)

        btn_layout.addStretch()

        close_btn = QPushButton(tr("app_settings.btn_close", "Kapat"))
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

        # ── Son ML İşlem Bilgisi ──
        self.last_op_label = QLabel("")
        self.last_op_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.last_op_label.setStyleSheet("color: #888; font-size: 9pt; margin-top: 4px;")
        layout.addWidget(self.last_op_label)

        self._refresh_table()
        self._refresh_last_operation_label()

    def _refresh_last_operation_label(self):
        """Proje config.ini'den son terminoloji işlemi bilgisini okur ve QLabel'ı günceller."""
        try:
            import configparser
            config_path = os.path.join(self.project_path, "config", "config.ini")
            if os.path.exists(config_path):
                cfg = configparser.ConfigParser()
                cfg.read(config_path, encoding="utf-8")
                last_start = cfg.getint("TerminologyOp", "last_start_chapter", fallback=0)
                last_end = cfg.getint("TerminologyOp", "last_end_chapter", fallback=0)
                if last_start > 0 and last_end > 0:
                    self.last_op_label.setText(
                        tr("ml_range.last_info", "Son İşlem: Başlangıç Bölümü: {start}, Bitiş Bölümü: {end}").format(start=last_start, end=last_end)
                    )
                    return
        except Exception:
            pass
        self.last_op_label.setText(tr("terminology.last_op_none", "Son İşlem: —"))

    def _refresh_table(self):
        from PyQt6.QtWidgets import QTableWidgetItem
        terms = self.manager.get_all_terms()
        self.table.setRowCount(len(terms))
        for row, t in enumerate(terms):
            self.table.setItem(row, 0, QTableWidgetItem(t.get("source", "")))
            self.table.setItem(row, 1, QTableWidgetItem(t.get("target", "")))
            self.table.setItem(row, 2, QTableWidgetItem(t.get("note", "")))

    def add_term(self):
        source = self.source_input.text().strip()
        target = self.target_input.text().strip()
        note = self.note_input.text().strip()
        if not source or not target:
            QMessageBox.warning(self, tr("prompt_editor.msg_missing_title", "Eksik"), tr("terminology.msg_missing_source_target", "Kaynak ve hedef terim gereklidir."))
            return
        self.manager.add_term(source, target, note)
        self.source_input.clear()
        self.target_input.clear()
        self.note_input.clear()
        self._refresh_table()

    def delete_term(self):
        row = self.table.currentRow()
        if row < 0:
            return
        source = self.table.item(row, 0).text()
        self.manager.remove_term(source)
        self._refresh_table()

    def import_terms(self):
        text, ok = QInputDialog.getMultiLineText(
            self, tr("terminology.btn_import", "📥 İçe Aktar"),
            tr("terminology.msg_import_body", "Her satıra bir terim girin (kaynak=hedef formatında):"),
            ""
        )
        if ok and text:
            count = self.manager.import_from_text(text)
            QMessageBox.information(self, tr("menu_bar.msg_save_success_title", "Başarılı"), tr("terminology.msg_imported_count", "{} terim içe aktarıldı.").format(count))
            self._refresh_table()

    def export_terms(self):
        text = self.manager.export_to_text()
        if not text:
            QMessageBox.information(self, tr("terminology.msg_empty_title", "Boş"), tr("terminology.msg_no_terms_to_export", "Dışa aktarılacak terim yok."))
            return

        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, tr("terminology.export_dialog_title", "Terimleri Kaydet"), "terminology.txt", "Text Files (*.txt)")
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(text)
            QMessageBox.information(self, tr("menu_bar.msg_save_success_title", "Başarılı"), tr("terminology.msg_exported_success", "Terimler kaydedildi: {}").format(path))

    def generate_from_scratch(self):
        reply = QMessageBox.question(
            self, tr("terminology.btn_generate", "⚡ Sıfırdan Üret"), 
            tr("terminology.msg_generate_confirm", "Mevcut terminolojiyi sıfırdan yapay zeka ile (dwnld klasöründeki dosyalar kullanılarak) üretmek istiyor musunuz?\n(Bu işlem bir süre alabilir)"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            QMessageBox.information(self, tr("theme_manager.msg_info_title", "Bilgi"), tr("terminology.msg_generate_info", "Arka planda (UI donmadan) çalışabilmesi için lütfen ana ekranda sağ panelde bulunan 'Yapay Zeka ile Terminoloji Üret' butonuna tıklayarak işlemi başlatın."))
            self.accept()

    def clear_terms(self):
        reply = QMessageBox.question(
            self, tr("terminology.btn_clear_all", "🧹 Tümünü Temizle"),
            tr("terminology.msg_clear_confirm", "Tüm terimleri silmek istediğinize emin misiniz?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.manager.clear()
            self._refresh_table()
