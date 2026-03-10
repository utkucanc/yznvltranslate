import os
import time
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from PyQt6.QtCore import pyqtSignal, QObject
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from logger import app_logger

class DownloadWorker(QObject):
    """
    Dosya indirme işlemini arayüzü dondurmadan arka planda yürüten işçi sınıfı.
    """
    finished = pyqtSignal()
    error = pyqtSignal(str)
    file_downloaded = pyqtSignal(str, str)  # İndirilen dosyanın tam yolu ve adı
    progress = pyqtSignal(int, int) # Mevcut sayfa ve toplam sayfa sayısı için
    
    def __init__(self, base_url, download_folder, max_pages=None, js_script_path=None):
        super().__init__()
        self.base_url = base_url
        self.download_folder = download_folder
        self.is_running = True
        self.max_pages = max_pages # İndirilecek maksimum sayfa sayısı
        self.downloaded_pages = 0
        self.js_script_path = js_script_path # JS dosyası yolu (None ise normal indirme)

    def run(self):
        """İndirme işlemini başlatan ana fonksiyon."""
        if self.js_script_path and os.path.exists(self.js_script_path):
            self._run_selenium()
        else:
            self._run_standard()
            
    def _run_selenium(self):
        """JS kodlarını Selenium üzerinden çalıştırarak indirir."""
        driver = None
        try:
            self.progress.emit(0, 100)
            
            # Chrome ayarlarını yapılandır
            chrome_options = Options()
            # chrome_options.add_argument("--headless") # Kullanıcının bot kontrolünü (cloudflare vs) aşması için headless kapalı önerilir, ancak eklenebilir.
            prefs = {"download.default_directory": self.download_folder,
                     "download.prompt_for_download": False,
                     "download.directory_upgrade": True}
            chrome_options.add_experimental_option("prefs", prefs)
            
            # WebDriver Başlat
            self.progress.emit(10, 100)
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            
            # Hedef URL'ye git
            self.progress.emit(20, 100)
            driver.get(self.base_url)
            
            # Kullanıcıya cloudflare aşması için biraz süre tanıyabiliriz veya script doğrudan bunu halledebilir.
            time.sleep(3) 

            # JS Dosyasını Oku
            with open(self.js_script_path, 'r', encoding='utf-8') as f:
                js_code = f.read()

            self.progress.emit(40, 100)
            
            # İndirme klasöründeki mevcut txt dosyalarını al (yeni geleni tespit etmek için)
            existing_files = set(f for f in os.listdir(self.download_folder) if f.endswith('.txt'))
            
            # JS Kodunu Enjekte Et ve Çalıştır
            # Not: .js dosyası bir IIFE (Immediately Invoked Function Expression) olduğu için await çalıştırması yapacak.
            driver.execute_script(js_code)
            
            self.progress.emit(60, 100)

            # Dosyanın inmesini bekle (Maksimum 10 dakika bekleyelim, büyük romanlar uzun sürebilir)
            wait_time = 0
            max_wait_time = 600 
            downloaded_file = None
            
            while wait_time < max_wait_time and self.is_running:
                current_files = set(f for f in os.listdir(self.download_folder) if f.endswith('.txt'))
                new_files = current_files - existing_files
                
                # Geçici indirme dosyalarını (crdownload vs) saymıyoruz (".txt" ile bittiği için sorun yok)
                if new_files:
                    downloaded_file = new_files.pop()
                    break
                    
                time.sleep(2)
                wait_time += 2
                
                # Progres barı yalandan biraz oynat (60-95 arası)
                simulated_progress = min(95, 60 + int((wait_time / max_wait_time) * 35))
                self.progress.emit(simulated_progress, 100)

            if not self.is_running:
                print("İndirme iptal edildi.")
                return

            if downloaded_file:
                # İndirme algılandı
                full_path = os.path.join(self.download_folder, downloaded_file)
                self.progress.emit(100, 100)
                self.file_downloaded.emit(full_path, downloaded_file)
            else:
                self.error.emit(f"Zaman aşımı: {max_wait_time} saniye boyunca indirme algılanamadı veya script hata verdi.")

        except Exception as e:
            self.error.emit(f"Selenium Hatası: {str(e)}")
        finally:
            if driver:
                driver.quit()
            self.finished.emit()
            print("Selenium işçisi tamamlandı/durduruldu.")


    def _run_standard(self):
        """İndirme işlemini başlatan ana fonksiyon."""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Referer": "https://www.google.com/",
                "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
            }
            session = requests.Session()
            current_url = self.base_url
            
            while self.is_running:
                if self.max_pages and self.downloaded_pages >= self.max_pages:
                    print("Maksimum sayfa sayısına ulaşıldı.")
                    break

                time.sleep(1) # Siteye saygılı olmak için bekleme süresi (ayarlanabilir)
                self.downloaded_pages += 1
                
                try:
                    response = session.get(current_url, headers=headers, timeout=15) # Zaman aşımı artırıldı
                    response.raise_for_status() # HTTP hataları için istisna fırlatır
                except requests.exceptions.HTTPError as http_err:
                    if response.status_code == 403:
                        raise Exception(f"Erişim engellendi (403): Site, isteği reddetti. IP adresiniz veya User-Agent'ınız engellenmiş olabilir.")
                    elif response.status_code == 404:
                        raise Exception(f"Sayfa bulunamadı (404): Hedef URL mevcut değil. Linki kontrol edin: {current_url}")
                    else:
                        raise Exception(f"HTTP Hatası: {http_err} - URL: {current_url}")
                except requests.exceptions.ConnectionError as conn_err:
                    raise Exception(f"Bağlantı Hatası: İnternet bağlantınızı veya URL'yi kontrol edin. {conn_err}")
                except requests.exceptions.Timeout as timeout_err:
                    raise Exception(f"Zaman Aşımı Hatası: Sunucu çok yavaş yanıt verdi. {timeout_err}")
                except requests.exceptions.RequestException as req_err:
                    raise Exception(f"Bir istek hatası oluştu: {req_err}")

                soup = BeautifulSoup(response.content, 'html.parser')
                # 'txtnav' sınıfını arayan veya doğrudan 'body' etiketini kullanan daha genel bir yaklaşım
                content_div = soup.find('div', {'id': 'novel_content'}) or soup.find('body')

                if content_div:
                    text_content = content_div.get_text(separator="\n", strip=True)
                    page_filename = f"page_{self.downloaded_pages:04}.txt"
                    full_path = os.path.join(self.download_folder, page_filename)
                    
                    with open(full_path, 'w', encoding='utf-8') as pf:
                        pf.write(text_content)
                    
                    self.file_downloaded.emit(full_path, page_filename)
                    self.progress.emit(self.downloaded_pages, self.max_pages if self.max_pages else 0) # İlerleme sinyali
                else:
                    print(f"Uyarı: İçerik bulunamadı! URL: {current_url}. Belki de sayfa yapısı değişti.")
                    # İçerik bulunamazsa yine de sonraki sayfaya geçmeye çalışabiliriz
                    
                # Sonraki sayfa düğmesini bulmak için daha esnek bir arama
                next_button = soup.find(lambda tag: tag.name == 'a' and ('下一章' in tag.text or 'next' in tag.text.lower() or 'ileri' in tag.text.lower() or "다음화 보기" in tag.text.lower()) or "다음화" in tag.text.lower())
                if next_button and next_button.has_attr('href'):
                    next_url = urljoin(current_url, next_button['href'])
                    # Sonsuz döngüyü engellemek için daha sağlam kontrol
                    if next_url == current_url or not next_url.startswith('http'): 
                        break
                    current_url = next_url
                else:
                    break # Son sayfaya ulaşıldı veya sonraki sayfa linki bulunamadı
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()
            print("İndirme işçisi tamamlandı/durduruldu.")

    def stop(self):
        """İndirme döngüsünü durdurur."""
        self.is_running = False
        print("İndirme işçisi durdurma isteği aldı.")
