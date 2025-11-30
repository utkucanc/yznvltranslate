import os
import google.generativeai as genai
from PyQt6.QtCore import QObject, pyqtSignal
import json # JSON modülü eklendi
import time # Yeniden deneme için eklendi

class TranslationWorker(QObject):
    """
    Dosya çeviri işlemini arayüzü dondurmadan arka planda yürüten işçi sınıfı.
    """
    finished = pyqtSignal(bool) # Kapatma durumu için bool eklendi
    error = pyqtSignal(str) # Genel hatalar için
    progress = pyqtSignal(int, int) # İlerleme: (mevcut_dosya_indeksi, toplam_dosya_sayısı)

    def __init__(self, input_folder, output_folder, api_key, startpromt):
        super().__init__()
        self.input_folder = input_folder
        self.output_folder = output_folder
        self.api_key = api_key
        self.prompt_prefix = startpromt # Başlangıç promtu
        self.is_running = True
        self.translation_errors = {} # Dosya bazında çeviri hatalarını saklamak için
        self.error_log_path = os.path.join(self.output_folder, 'translation_errors.json')
        self.shutdown_on_finish = False # Kapatma bayrağı

        # API anahtarını yapılandır
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash-preview-09-2025')
        else:
            self.model = None

    def run(self):
        if not self.model:
            self.error.emit("Gemini API anahtarı yapılandırılmamış. Çeviri yapılamaz.")
            self.finished.emit(self.shutdown_on_finish) # Bayrakla emit et
            return

        # Mevcut hata logunu yükle (varsa)
        if os.path.exists(self.error_log_path):
            try:
                with open(self.error_log_path, 'r', encoding='utf-8') as f:
                    self.translation_errors = json.load(f)
            except json.JSONDecodeError:
                self.translation_errors = {} # JSON bozuksa sıfırla
            except Exception as e:
                print(f"Uyarı: Mevcut çeviri hata logu yüklenirken hata oluştu: {e}")
                self.translation_errors = {}

        try:
            files_to_translate = sorted([f for f in os.listdir(self.input_folder) if f.endswith('.txt')])
            total_files = len(files_to_translate)
            
            for i, file_name in enumerate(files_to_translate):
                if not self.is_running:
                    break

                original_file_path = os.path.join(self.input_folder, file_name)
                translated_file_name = f"translated_{file_name}"
                translated_file_path = os.path.join(self.output_folder, translated_file_name)

                # Eğer dosya daha önce başarıyla çevrilmişse ve hata logunda yoksa atla
                if os.path.exists(translated_file_path) and file_name not in self.translation_errors:
                    self.progress.emit(i + 1, total_files)
                    continue

                try:
                    with open(original_file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except Exception as e:
                    self.translation_errors[file_name] = f"Okuma Hatası: {str(e)}"
                    self.progress.emit(i + 1, total_files)
                    continue

                full_prompt = self.prompt_prefix +"\n\n"+ content
                
                # Hata 500 için yeniden deneme mekanizması
                MAX_RETRIES = 3
                retry_count = 0
                translated_text = None
                last_error = ""

                while retry_count < MAX_RETRIES:
                    if not self.is_running:
                        break # Durdurma isteği (iç döngü)

                    try:
                        response = self.model.generate_content(full_prompt)
                        
                        # --- DÜZELTME 1: Yanıtı doğru alma ve engelleme kontrolü ---
                        if response.prompt_feedback and response.prompt_feedback.block_reason:
                            block_reason_name = response.prompt_feedback.block_reason.name
                            # Engellenen istekleri yeniden deneme (genellikle sonuç değişmez)
                            raise Exception(f"İçerik engellendi: {block_reason_name}")

                        if not response.candidates or not response.candidates[0].content or not response.candidates[0].content.parts:
                            # Boş yanıtları yeniden deneme (geçici bir sorun olabilir)
                            raise Exception("API'den boş veya geçersiz yanıt alındı.")
                            
                        translated_text = response.candidates[0].content.parts[0].text
                        # --- DÜZELTME 1 SONU ---
                        
                        # Başarı: Hata yoksa veya varsa kaldır
                        if file_name in self.translation_errors:
                            del self.translation_errors[file_name]
                        break # Başarılı, while döngüsünden çık
                    
                    except Exception as e:
                        last_error = str(e)
                        # Hata 500 içeriyorsa ve deneme hakkı varsa
                        if "500" in last_error and retry_count < MAX_RETRIES - 1:
                            retry_count += 1
                            wait_time = 2 ** retry_count # 2, 4 saniye
                            print(f"'{file_name}' için 500 Hatası. {wait_time}sn sonra yeniden denenecek... ({retry_count}/{MAX_RETRIES})")
                            
                            # Uykuyu bölerek durdurma isteğini kontrol et
                            sleep_start = time.time()
                            while time.time() - sleep_start < wait_time:
                                if not self.is_running:
                                    break
                                time.sleep(0.5)
                            
                            if not self.is_running:
                                break # sleep sırasında durdurma isteği geldi
                        
                        else:
                            # 500 hatası değilse, engellendiyse veya deneme hakkı bittiyse
                            self.translation_errors[file_name] = f"Çeviri Hatası: {last_error}"
                            # Hata durumunda da dosyaya yaz (kullanıcı hatayı görsün)
                            try:
                                with open(translated_file_path, 'w', encoding='utf-8') as f:
                                    f.write(f"Çeviri hatası: {last_error}\n\nOrijinal Metin:\n{content[:500]}...") # Hata ve orijinal metnin bir kısmı
                            except Exception as write_e:
                                print(f"Hata dosyası yazılırken hata oluştu: {write_e}")
                            break # Hata kalıcı, while döngüsünden çık
                
                if not self.is_running:
                    break # Ana for döngüsünden de çık

                # While döngüsü bittikten sonra, eğer çeviri başarılı olduysa yaz
                if translated_text is not None:
                     with open(translated_file_path, 'w', encoding='utf-8') as f:
                        f.write(translated_text)
                
                self.progress.emit(i + 1, total_files)

        except Exception as e:
            self.error.emit(f"Genel çeviri işlemi hatası: {str(e)}")
        finally:
            # Hata logunu kaydet
            try:
                with open(self.error_log_path, 'w', encoding='utf-8') as f:
                    json.dump(self.translation_errors, f, indent=4, ensure_ascii=False)
            except Exception as e:
                print(f"Hata logu kaydedilirken hata oluştu: {e}")

            # --- DÜZELTME 2: İşlem bittiğinde sinyal gönder ---
            self.finished.emit(self.shutdown_on_finish)
