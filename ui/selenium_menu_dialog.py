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
from ui.post_download_dialog import PostDownloadDialog

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
    combobox.addItem("Seçiniz...", None)
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


class SeleniumMenuDialog(QDialog):
    """Selenium ile indirme yaparken Cloudflare ve JS yönetimi için diyalog."""
    def __init__(self, worker, parent=None):
        super().__init__(parent)
        self.worker = worker
        self.setWindowTitle("Selenium Kontrol Paneli")
        self.setFixedWidth(500)
        # Pencereyi her zaman üstte tut özelliği kaldırıldı (istek üzerine)
        # self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        
        layout = QVBoxLayout(self)
        
        info_label = QLabel("Açılan tarayıcıda Cloudflare veya bot kontrolünü aşın. "
                            "Kitabın ilk bölüm sayfasına geldiğinizde butonları kullanın.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("margin-bottom: 10px; color: #E0E0E0;")
        layout.addWidget(info_label)
        
        self.opened_btn = QPushButton("1. İçerik 1. bölümü açıldı")
        self.opened_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 12px; font-weight: bold; border-radius: 5px;")
        self.opened_btn.clicked.connect(self.on_opened_clicked)
        layout.addWidget(self.opened_btn)
        
        self.shuba_btn = QPushButton("2. 69shubao için indirmeyi başlat")
        self.shuba_btn.setEnabled(False)
        # Başlangıçta pasif/gri stil
        self.shuba_btn.setStyleSheet("background-color: #9E9E9E; color: #E0E0E0; padding: 10px; border-radius: 5px;")
        self.shuba_btn.clicked.connect(lambda: self.start_download("shuba"))
        layout.addWidget(self.shuba_btn)
        
        self.booktoki_btn = QPushButton("3. booktoki için indirmeyi başlat")
        self.booktoki_btn.setEnabled(False)
        self.booktoki_btn.setStyleSheet("background-color: #9E9E9E; color: #E0E0E0; padding: 10px; border-radius: 5px;")
        self.booktoki_btn.clicked.connect(lambda: self.start_download("booktoki"))
        layout.addWidget(self.booktoki_btn)

        self.novelfire_btn = QPushButton("4. novelfire için indirmeyi başlat")
        self.novelfire_btn.setEnabled(False)
        self.novelfire_btn.setStyleSheet("background-color: #9E9E9E; color: #E0E0E0; padding: 10px; border-radius: 5px;")
        self.novelfire_btn.clicked.connect(lambda: self.start_download("novelfire"))
        layout.addWidget(self.novelfire_btn)
        
        self.cancel_btn = QPushButton("İptal et")
        self.cancel_btn.setStyleSheet("margin-top: 10px; padding: 5px;")
        self.cancel_btn.clicked.connect(self.on_cancel_clicked)
        layout.addWidget(self.cancel_btn)
        
        # Durum bilgisi için etiket
        self.status_label = QLabel("Bekleniyor...")
        self.status_label.setStyleSheet("color: #4CAF50; font-style: italic; margin-top: 5px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        self.current_running_btn = None
        self.is_finished_signal_received = False # Çoklu uyarıyı engellemek için
        
        # Worker sinyallerini dinle
        self.worker.file_downloaded.connect(self.on_download_finished)
        self.worker.error.connect(self.on_download_error)
        if hasattr(self.worker, 'status_message'):
            self.worker.status_message.connect(self.update_status_label)

    def update_status_label(self, message):
        """Worker'dan gelen durum mesajını günceller."""
        self.status_label.setText(message)
        # Eğer mesajda "alınıyor" geçiyorsa sarı renkle vurgula
        if "alınıyor" in message.lower():
            self.status_label.setStyleSheet("color: #FFC107; font-weight: bold; padding-left: 10px;")
        else:
            self.status_label.setStyleSheet("color: #4CAF50; font-style: italic; padding-left: 10px;")

    def on_opened_clicked(self):
        """1. Bölüm açıldığında diğer butonları mavi ve aktif yapar."""
        app_logger.info("SeleniumMenuDialog: '1. Bölüm açıldı' tıklandı.")
        blue_style = "background-color: #2196F3; color: white; padding: 10px; font-weight: bold; border-radius: 5px;"
        self.shuba_btn.setEnabled(True)
        self.shuba_btn.setStyleSheet(blue_style)
        self.booktoki_btn.setEnabled(True)
        self.booktoki_btn.setStyleSheet(blue_style)
        self.novelfire_btn.setEnabled(True)
        self.novelfire_btn.setStyleSheet(blue_style)
        
        self.opened_btn.setEnabled(False)
        self.opened_btn.setText("✅ Bölüm Hazır")
        self.opened_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 12px; font-weight: bold; border-radius: 5px;")
        
    def start_download(self, site):
        """İndirmeyi başlatır. Seçilen buton sarı, diğeri gri olur."""
        if site == "booktoki":
            count, ok = QInputDialog.getInt(self, "Bölüm Sayısı", "Kaç bölüm indirilecek?", self.worker.selenium_chapter_limit, 1, 10000)
            if not ok: return
            self.worker.selenium_chapter_limit = count
            self.current_running_btn = self.booktoki_btn
            other_btn = self.shuba_btn
        elif site == "novelfire":
            self.current_running_btn = self.novelfire_btn
            other_btn = self.booktoki_btn
        else:
            self.current_running_btn = self.shuba_btn
            other_btn = self.booktoki_btn

        # UI Güncelleme (Sarı: Çalışıyor, Gri: Devre Dışı)
        self.current_running_btn.setText("⏳ İndiriliyor...")
        self.current_running_btn.setStyleSheet("background-color: #FFC107; color: black; padding: 10px; font-weight: bold; border-radius: 5px;")
        self.current_running_btn.setEnabled(False)
        
        other_btn.setEnabled(False)
        other_btn.setStyleSheet("background-color: #9E9E9E; color: #E0E0E0; padding: 10px; border-radius: 5px;")
        
        # Worker'a komutu gönder
        app_logger.info(f"SeleniumMenuDialog: İndirme başlatılıyor: {site}")
        self.worker.selenium_command = site

    def on_download_finished(self, path, name):
        """İndirme bittiğinde butonu yeşil yapar."""
        if self.is_finished_signal_received:
            return
        self.is_finished_signal_received = True

        if self.current_running_btn:
            self.current_running_btn.setText("✅ Tamamlandı")
            self.current_running_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px; font-weight: bold; border-radius: 5px;")
        
        self.status_label.setText("✅ İşlem Başarıyla Tamamlandı")
        # QMessageBox.information(self, "Başarılı", f"İndirme tamamlandı:\n{name}") # Eski basit uyarı
        
        # Yeni aksiyon diyaloğunu aç
        post_dlg = PostDownloadDialog(path, name, self)
        post_dlg.exec()
        
        # Aksiyon bittikten sonra Selenium menüsünü de kapatabiliriz
        self.accept()

    def on_download_error(self, message):
        """Hata durumunda butonu eski haline getir veya uyar."""
        if self.current_running_btn:
            self.current_running_btn.setText("❌ Hata")
            self.current_running_btn.setStyleSheet("background-color: #F44336; color: white; padding: 10px; font-weight: bold; border-radius: 5px;")
        QMessageBox.critical(self, "Hata", f"İndirme sırasında hata oluştu:\n{message}")

    def on_cancel_clicked(self):
        app_logger.info("SeleniumMenuDialog: Kullanıcı iptal butonuna bastı.")
        self.worker.selenium_command = "cancel"
        self.reject()
