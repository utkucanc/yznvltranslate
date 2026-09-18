"""
core/startup_worker.py — Arka planda açılış yükleme işlemlerini gerçekleştiren worker.

QThread tabanlı StartupWorker sınıfı:
  - Ağır I/O, ayar okuma, proje listesi tarama, matplotlib ön yükleme vb. adımları çalıştırır.
  - progress(str) sinyali ile splash ekranına bilgi gönderir.
  - finished(dict) sinyali ile toplanan açılış verilerini MainWindow'a aktarır.
"""

from PyQt6 import QtWidgets
from core.path_resolver import get_project_dir
from logger import app_logger
from core.project_manager import ProjectManager
import os
from PyQt6.QtCore import QThread, pyqtSignal
import time


class StartupWorker(QThread):
    """
    Açılış işlemlerini arka planda yürüten Thread.
    """
    progress = pyqtSignal(str)
    finished = pyqtSignal(dict)

    def __init__(self, base_dir: str = None, parent=None):
        super().__init__(parent)
        self.base_dir = base_dir or os.getcwd()

    def run(self):
        startup_data = {}

        try:
            # 1. Adım: Uygulama ayarlarını yükle
            self.progress.emit("Uygulama ayarları yükleniyor...")
            from ui.app_settings_dialog import load_app_settings
            app_settings = load_app_settings()
            startup_data["app_settings"] = app_settings
            

            # 2. Adım: İstek sayacı verilerini yükle
            self.progress.emit("İstek istatistikleri hazırlanıyor...")
            from ui.request_counter_manager import RequestCounterManager
            request_counter_mgr = RequestCounterManager()
            startup_data["request_counter_mgr"] = request_counter_mgr
            

            # 3. Adım: Proje dizinlerini tara ve listeyi oluştur
            self.progress.emit("Proje verileri okunuyor...")
            projects = self._scan_projects()
            startup_data["projects"] = projects
            

            # 4. Adım: Grafik ve ağır kütüphaneleri ön yükle
            self.progress.emit("Grafik modülleri hazırlanıyor...")
            try:
                import matplotlib
                matplotlib.use("QtAgg")
                import matplotlib.pyplot as plt
            except Exception:
                pass
            # 5. Adım: Arayüz hazırlığı tamamlanıyor
            self.progress.emit("Sistem bileşenleri tamamlanıyor...")
            self.msleep(150)

            # 6. Adım: FileListManager ile veritabanını senkronize et
            self._presync_default_project_db()
            

        except Exception as e:
            startup_data["error"] = str(e)

        self.finished.emit(startup_data)

    def _presync_default_project_db(self):
        """
        Açılışta tüm projeleri tarar; veritabanı olmayan projelere otomatik veri tabanı aktarımı uygular.
        """
        try:
            from core.database_manager import DatabaseManager
            from core.file_list_manager import FileListManager

            projects = ProjectManager(os.getcwd()).list_projects()
            if not projects:
                app_logger.debug("Presync: Proje bulunamadı, atlanıyor.")
                return

            migrated = 0
            for project_name in projects:
                try:
                    project_path = get_project_dir(os.getcwd(), project_name)
                    db_manager = DatabaseManager(project_path)
                    if not db_manager.db_exists():
                        self.progress.emit(f"'{project_name}' için veritabanı oluşturuluyor...")
                        flm = FileListManager(project_path)
                        success = db_manager.sync_directory_to_db(flm)
                        if success:
                            migrated += 1
                            app_logger.info(f"Presync: '{project_name}' projesi başarıyla veritabanına aktarıldı.")
                        else:
                            app_logger.warning(f"Presync: '{project_name}' veritabanına aktarılması başarısız.")
                except Exception as proj_err:
                    app_logger.warning(f"Presync: '{project_name}' için hata: {proj_err}")

            if migrated > 0:
                app_logger.info(f"Presync: Toplam {migrated} proje veritabanına aktarıldı.")

        except Exception as e:
            app_logger.error(f"Veritabanı senkronizasyonu hatası: {str(e)}")    
            
            
            
            
    def _scan_projects(self) -> list:
        """Mevcut proje dizinlerini tarar."""
        projects = []
        try:
            # Project/ klasörü altındakiler
            proj_dir = os.path.join(self.base_dir, "Project")
            if os.path.exists(proj_dir):
                for p in sorted(os.listdir(proj_dir)):
                    p_path = os.path.join(proj_dir, p)
                    if os.path.isdir(p_path) and not p.startswith("."):
                        projects.append(p)

            # Kök dizindeki eski projeler
            for p in sorted(os.listdir(self.base_dir)):
                p_path = os.path.join(self.base_dir, p)
                if os.path.isdir(p_path) and not p.startswith(".") and p not in ("Project", "AppConfigs", "core", "ui", "build", "dist", "__pycache__"):
                    config_file = os.path.join(p_path, "config.ini")
                    old_config = os.path.join(p_path, "config", "config.ini")
                    if os.path.exists(config_file) or os.path.exists(old_config):
                        if p not in projects:
                            projects.append(p)
        except Exception:
            pass
        return projects
