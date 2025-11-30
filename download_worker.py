import os
import time
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from PyQt6.QtCore import pyqtSignal, QObject

class DownloadWorker(QObject):
    """
    Dosya indirme işlemini arayüzü dondurmadan arka planda yürüten işçi sınıfı.
    """
    finished = pyqtSignal()
    error = pyqtSignal(str)
    file_downloaded = pyqtSignal(str, str)  # İndirilen dosyanın tam yolu ve adı
    progress = pyqtSignal(int, int) # Mevcut sayfa ve toplam sayfa sayısı için
    
    def __init__(self, base_url, download_folder, max_pages=None):
        super().__init__()
        self.base_url = base_url
        self.download_folder = download_folder
        self.is_running = True
        self.max_pages = max_pages # İndirilecek maksimum sayfa sayısı
        self.downloaded_pages = 0

    def run(self):
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
