"""
WorkflowDownloadWorker — Workflow için Cloudflare kontrollü sessiz indirme worker'ı.

Mevcut DownloadWorker'ı temel alır, ek olarak:
  - Cloudflare bot koruması otomatik algılama
  - Kullanıcı onayı gerektiren/gerektirmeyen akış ayrımı
  - Sessiz (headless) bitiş — QMessageBox yok
"""

import os
import time
import datetime
from PyQt6.QtCore import pyqtSignal, QObject
from logger import app_logger


class WorkflowDownloadWorker(QObject):
    """Workflow için Cloudflare kontrollü Selenium indirme worker'ı."""

    finished = pyqtSignal()
    error = pyqtSignal(str)
    progress = pyqtSignal(int, int)
    status_message = pyqtSignal(str)
    file_downloaded = pyqtSignal(str, str)  # (tam yol, dosya adı)

    # Cloudflare algılandığında kullanıcı müdahalesi gerektiğini bildirir
    cloudflare_detected = pyqtSignal()

    def __init__(self, base_url: str, download_folder: str,
                 site: str = "booktoki", chapter_limit: int = 120):
        super().__init__()
        self.base_url = base_url
        self.download_folder = download_folder
        self.site = site  # "booktoki", "shuba", "novelfire"
        self.chapter_limit = chapter_limit
        self.is_running = True

        # CF kontrol sonrası kullanıcıdan gelecek onay
        self.user_confirmed = False
        # İndirme başlatma komutu (cloudflare sonrası kullanıcı onaylarsa)
        self.selenium_command = None

    # Cloudflare Algılama 

    @staticmethod
    def _check_cloudflare(driver) -> bool:
        """Sayfa kaynağında Cloudflare bot koruması imzalarını arar."""
        try:
            page_source = driver.page_source
            cf_indicators = [
                'href="https://www.cloudflare.com?utm_source=challenge',
                'id="privacy-link"',
                'href="https://www.cloudflare.com/privacypolicy/"',
                'class="footer-text"',
            ]
            # En az 2 gösterge varsa Cloudflare
            found = sum(1 for ind in cf_indicators if ind in page_source)
            return found >= 2
        except Exception as e:
            app_logger.warning(f"Cloudflare kontrolünde hata: {e}")
            return False

    # JS Dosya Yolu 

    def _get_js_path(self) -> str | None:
        """Site adına göre JS dosya yolunu döndürür."""
        js_map = {
            "booktoki": "booktoki.js",
            "shuba": "69shuba.js",
            "novelfire": "novelfire.js",
        }
        filename = js_map.get(self.site)
        if not filename:
            return None
        path = os.path.join(os.getcwd(), filename)
        if not os.path.exists(path):
            # JS oluşturma denemesi
            try:
                from core.js_create import create_js_file
                create_js_file(filename)
            except Exception:
                pass
        return path if os.path.exists(path) else None

    # Ana Çalışma

    def run(self):
        """İndirme işlemini başlatır."""
        driver = None
        app_logger.info(f"WorkflowDownloadWorker başlatıldı: site={self.site}, url={self.base_url}")

        try:
            self.progress.emit(0, 100)
            self.status_message.emit("Tarayıcı hazırlanıyor...")

            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager

            chrome_options = Options()
            chrome_options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
            prefs = {
                "download.default_directory": self.download_folder,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True
            }
            chrome_options.add_experimental_option("prefs", prefs)

            self.progress.emit(10, 100)
            app_logger.info("WebDriver kuruluyor...")
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=chrome_options
            )

            # Hedef URL'ye git
            self.progress.emit(20, 100)
            self.status_message.emit("Siteye bağlanılıyor...")
            app_logger.info(f"URL açılıyor: {self.base_url}")
            driver.get(self.base_url)

            # Sayfanın yüklenmesini bekle
            time.sleep(3)

            # ── Cloudflare Kontrolü ──
            self.progress.emit(25, 100)
            if self._check_cloudflare(driver):
                app_logger.info("Cloudflare bot koruması algılandı. Kullanıcı onayı bekleniyor.")
                self.status_message.emit("⚠️ Cloudflare algılandı — Kullanıcı onayı bekleniyor...")
                self.cloudflare_detected.emit()

                # Kullanıcıdan onay bekle
                while not self.user_confirmed and self.is_running:
                    time.sleep(1)

                if not self.is_running:
                    app_logger.warning("İndirme iptal edildi (CF aşamasında).")
                    return
            else:
                app_logger.info("Cloudflare algılanmadı, doğrudan indirmeye geçiliyor.")
                self.status_message.emit("✅ Cloudflare yok — İndirme hazırlanıyor...")
                # Otomatik komut ata
                self.selenium_command = self.site

            # Kullanıcı CF'yi geçtiyse ama komut vermemişse, site'ı ata
            if self.selenium_command is None:
                self.selenium_command = self.site

            if self.selenium_command == "cancel":
                app_logger.warning("İndirme kullanıcı tarafından iptal edildi.")
                return

            # ── JS Script Hazırlık ──
            actual_js_path = self._get_js_path()
            if not actual_js_path:
                msg = f"JS dosyası bulunamadı: {self.site}"
                app_logger.error(msg)
                self.error.emit(msg)
                return

            # Booktoki için bölüm limiti güncelle
            if self.site == "booktoki" and os.path.exists(actual_js_path):
                self._update_booktoki_limit(actual_js_path)

            # ── JS Enjeksiyonu ──
            with open(actual_js_path, 'r', encoding='utf-8') as f:
                js_code = f.read()

            self.progress.emit(40, 100)
            self.status_message.emit("JavaScript enjekte ediliyor...")
            app_logger.info(f"Script enjekte ediliyor: {os.path.basename(actual_js_path)}")

            existing_files = set(f for f in os.listdir(self.download_folder) if f.endswith('.txt'))
            driver.execute_script(js_code)

            self.progress.emit(60, 100)
            app_logger.info("Script çalıştırıldı, indirme bekleniyor...")

            # ── Dosya İnmesini Bekle ──
            elapsed_time = 0
            downloaded_file = None
            LOG_PROGRESS_INTERVAL = 60

            while self.is_running:
                # Tarayıcı hâlâ açık mı?
                try:
                    _ = driver.window_handles
                except Exception as e:
                    error_msg = f"Tarayıcı beklenmedik kapandı: {e}"
                    app_logger.error(error_msg)
                    self.error.emit(error_msg)
                    return

                # Browser loglarını oku
                now = datetime.datetime.now()
                try:
                    logs = driver.get_log('browser')
                    for entry in logs:
                        msg = entry.get('message', '')
                        if '📄' in msg or 'bölüm' in msg.lower():
                            clean_msg = msg.split('"')[-2] if '"' in msg else msg
                            self.status_message.emit(clean_msg)
                            app_logger.info(f"Time: {now} - JS: {clean_msg}")
                except Exception:
                    pass

                # Dosya kontrolü
                current_files = set(f for f in os.listdir(self.download_folder) if f.endswith('.txt'))
                new_files = current_files - existing_files
                if new_files:
                    downloaded_file = list(new_files)[0]
                    app_logger.info(f"Yeni dosya tespit edildi: {downloaded_file}")
                    break

                time.sleep(3)
                elapsed_time += 3
                simulated_progress = min(98, 60 + int((elapsed_time / 3600) * 38))
                self.progress.emit(simulated_progress, 100)

                if elapsed_time % LOG_PROGRESS_INTERVAL == 0 and elapsed_time > 0:
                    app_logger.info(f"İndirme devam ediyor... {elapsed_time // 60}dk {elapsed_time % 60}sn")

            if not self.is_running:
                app_logger.warning("Durma sinyali alındı.")
                return

            if downloaded_file:
                full_path = os.path.join(self.download_folder, downloaded_file)
                self.progress.emit(100, 100)
                self.status_message.emit("✅ İndirme tamamlandı!")
                app_logger.info(f"Workflow indirme başarılı: {full_path}")
                self.file_downloaded.emit(full_path, downloaded_file)
            else:
                error_msg = "İndirme tamamlandı ancak yeni dosya tespit edilemedi."
                app_logger.error(error_msg)
                self.error.emit(error_msg)

        except Exception as e:
            app_logger.critical(f"Workflow Selenium Hatası: {str(e)}", exc_info=True)
            self.error.emit(f"Selenium Hatası: {str(e)}")
        finally:
            if driver:
                try:
                    app_logger.info("Tarayıcı kapatılıyor...")
                    driver.quit()
                except Exception:
                    pass
            self.finished.emit()
            app_logger.info("WorkflowDownloadWorker oturumu kapattı.")

    def _update_booktoki_limit(self, js_path: str):
        """Booktoki JS dosyasındaki bölüm limitini günceller."""
        try:
            with open(js_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            for i, line in enumerate(lines):
                if 'if (counter>=' in line:
                    lines[i] = f"        if (counter>= {self.chapter_limit}){{\n"
                    break
            with open(js_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            app_logger.info(f"Booktoki limit güncellendi: {self.chapter_limit}")
        except Exception as e:
            app_logger.warning(f"Booktoki limit güncellenemedi: {e}")

    def stop(self):
        """İndirme döngüsünü durdurur."""
        self.is_running = False
        app_logger.info("WorkflowDownloadWorker durdurma isteği aldı.")
