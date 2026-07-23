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


class PostDownloadDialog(QDialog):
    """İndirme bittiğinde kullanıcıya sunulan aksiyonlar (Klasör Aç, Ayır, Kapat)."""
    def __init__(self, file_path, file_name, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.file_name = file_name
        self.setWindowTitle(tr("post_download.window_title", "İndirme Tamamlandı"))
        self.setFixedWidth(450)
        
        layout = QVBoxLayout(self)
        
        # Bilgi Mesajı
        title_label = QLabel(tr("post_download.title", "✅ İndirme İşlemi Başarılı"))
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #4CAF50; margin-bottom: 5px;")
        layout.addWidget(title_label)
        
        info_label = QLabel(tr("post_download.info", "İndirilen dosya:\n{filename}").format(filename=self.file_name))
        info_label.setWordWrap(True)
        info_label.setStyleSheet("margin-bottom: 20px; color: #E0E0E0;")
        layout.addWidget(info_label)
        
        # Butonlar
        btn_layout = QVBoxLayout()
        
        self.open_path_btn = QPushButton(tr("post_download.btn_open_folder", "📁 Dosya Yolunu Aç"))
        self.open_path_btn.setStyleSheet("padding: 10px; background-color: #2196F3; color: white;")
        self.open_path_btn.clicked.connect(self.open_folder)
        btn_layout.addWidget(self.open_path_btn)
        
        self.split_btn = QPushButton(tr("post_download.btn_split", "✂️ Bölümleri Ayır (Split)"))
        self.split_btn.setStyleSheet("padding: 10px; background-color: #9C27B0; color: white;")
        self.split_btn.clicked.connect(self.start_splitting)
        btn_layout.addWidget(self.split_btn)
        
        self.close_btn = QPushButton(tr("post_download.btn_close", "🚪 Kapat - Ana Ekrana Dön"))
        self.close_btn.setStyleSheet("padding: 10px; margin-top: 10px;")
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)
        
        layout.addLayout(btn_layout)
        
        # İlerleme Çubuğu (Başlangıçta gizli)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("margin-top: 10px;")
        layout.addWidget(self.progress_bar)
        
        self.split_thread = None
        self.split_worker = None

    def open_folder(self):
        """Dosyanın bulunduğu klasörü açar."""
        folder = os.path.dirname(self.file_path)
        try:
            # Windows için klasörü aç
            os.startfile(folder)
            app_logger.info(f"PostDownloadDialog: Klasör açıldı -> {folder}")
        except Exception as e:
            # Diğer OS'ler veya hata durumu için alternatif
            import platform
            try:
                if platform.system() == "Windows":
                    os.startfile(folder)
                elif platform.system() == "Darwin":
                    import subprocess
                    subprocess.Popen(["open", folder])
                else:
                    import subprocess
                    subprocess.Popen(["xdg-open", folder])
            except:
                QMessageBox.warning(self, tr("main_window.msg_structure_error_title", "Hata"), tr("post_download.msg_folder_open_error", "Klasör açılamadı: {}").format(e))

    def start_splitting(self):
        """SplitWorker başlatarak bölümleri ayırır."""
        from core.workers.split_worker import SplitWorker # Import yerel
        
        # output_folder = os.path.join(os.path.dirname(self.file_path), os.path.splitext(self.file_name)[0] + "_bolumler")
        # print(output_folder)
        # print(self.file_path)
        # print(self.file_name)
        output_folder = os.path.dirname(self.file_path)
        self.split_btn.setEnabled(False)
        self.close_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.split_thread = QThread()
        self.split_worker = SplitWorker(self.file_path, output_folder)
        self.split_worker.moveToThread(self.split_thread)
        
        self.split_thread.started.connect(self.split_worker.run)
        self.split_worker.progress.connect(self.update_progress)
        self.split_worker.finished.connect(self.on_split_finished)
        self.split_worker.error.connect(self.on_split_error)
        
        self.split_thread.start()
        app_logger.info(f"PostDownloadDialog: Bölüm ayırma başlatıldı -> {output_folder}")

    def update_progress(self, current, total):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)

    def on_split_finished(self):
        self.split_thread.quit()
        self.split_thread.wait()
        # Orijinal dosyayı cmplt klasörüne taşı
        dest_path = ""
        try:
            import shutil
            # Proje yolunu dwnld klasöründen iki üst dizin olarak bul
            project_path = os.path.dirname(os.path.dirname(self.file_path))
            project_name = os.path.basename(project_path)
            cmplt_folder = os.path.join(project_path, 'cmplt')
            os.makedirs(cmplt_folder, exist_ok=True)
            new_name = f"{project_name}-Tümbolumler.txt"
            dest_path = os.path.join(cmplt_folder, new_name)
            shutil.move(self.file_path, dest_path)
            app_logger.info(f"PostDownloadDialog: Orijinal dosya taşındı -> {dest_path}")
        except Exception as e:
            app_logger.warning(f"PostDownloadDialog: Dosya taşıma hatası: {e}")
        self.progress_bar.setVisible(False)
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(tr("post_download.msg_split_finished_title", "Bölümler Ayrıldı"))
        msg_box.setText(tr("post_download.msg_split_finished_body", "Bölümler başarıyla ayrıldı.\nOrijinal tüm bölümler dosyası 'cmplt' klasörüne taşındı:\n\n{path}\n\nBu dosya saklansın mı, silinsin mi?").format(path=dest_path))
        msg_box.setIcon(QMessageBox.Icon.Question)
        keep_btn = msg_box.addButton(tr("post_download.btn_keep", "Sakla"), QMessageBox.ButtonRole.AcceptRole)
        delete_btn = msg_box.addButton(tr("post_download.btn_delete", "Sil"), QMessageBox.ButtonRole.DestructiveRole)
        msg_box.setDefaultButton(keep_btn)
        msg_box.exec()
        if msg_box.clickedButton() == delete_btn:
            try:
                os.remove(dest_path)
                app_logger.info(f"PostDownloadDialog: Tüm bölümler dosyası silindi -> {dest_path}")
            except Exception as e:
                app_logger.warning(f"PostDownloadDialog: Dosya silme hatası: {e}")
        else:
            app_logger.info(f"PostDownloadDialog: Tüm bölümler dosyası saklandı -> {dest_path}")
        app_logger.info("PostDownloadDialog: Bölüm ayırma tamamlandı.")
        self.accept()

    def on_split_error(self, message):
        self.split_thread.quit()
        self.split_thread.wait()
        
        self.split_btn.setEnabled(True)
        self.close_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, tr("main_window.msg_structure_error_title", "Hata"), tr("post_download.msg_split_error", "Ayırma hatası: {}").format(message))
        app_logger.error(f"PostDownloadDialog: Ayırma hatası -> {message}")
