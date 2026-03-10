import os
import google.generativeai as genai
from PyQt6.QtCore import QObject, pyqtSignal
import json
import time
from logger import app_logger

class TranslationWorker(QObject):
    """
    Dosya çeviri işlemini arayüzü dondurmadan arka planda yürüten işçi sınıfı.
    """
    finished = pyqtSignal(bool) # Kapatma durumu için bool
    error = pyqtSignal(str) 
    progress = pyqtSignal(int, int) 

    # __init__ metoduna file_limit ve max_retries eklendi
    def __init__(self, input_folder, output_folder, api_key, startpromt, model_version="gemini-2.5-flash-preview-09-2025", file_limit=None, max_retries=3):
        super().__init__()
        self.input_folder = input_folder
        self.output_folder = output_folder
        self.api_key = api_key
        self.prompt_prefix = startpromt
        self.model_version = model_version
        self.file_limit = file_limit # Limiti kaydet
        self.max_retries = max_retries # Retry sayısını kaydet
        self.is_running = True
        self.is_paused = False
        self.translation_errors = {}
        self.error_log_path = os.path.join(self.output_folder, 'translation_errors.json')
        self.shutdown_on_finish = False

        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_version)
        else:
            self.model = None

    def pause(self):
        """Çeviriyi duraklatır."""
        self.is_paused = True

    def resume(self):
        """Çeviriyi devam ettirir."""
        self.is_paused = False

    def run(self):
        if not self.model:
            self.error.emit("Gemini API anahtarı veya Model yapılandırılmamış.")
            self.finished.emit(self.shutdown_on_finish)
            return

        # Hata logunu yükle
        if os.path.exists(self.error_log_path):
            try:
                with open(self.error_log_path, 'r', encoding='utf-8') as f:
                    self.translation_errors = json.load(f)
            except:
                self.translation_errors = {}

        try:
            time.sleep(0.5)
            files_to_translate = sorted([f for f in os.listdir(self.input_folder) if f.endswith('.txt')])
            total_files = len(files_to_translate)
            
            translated_count_session = 0 # Bu oturumda kaç dosya çevrildiğini sayar

            for i, file_name in enumerate(files_to_translate):
                # Duraklatma Döngüsü
                while self.is_paused and self.is_running:
                    time.sleep(0.5)

                if not self.is_running:
                    break
                
                # --- YENİ: Limit Kontrolü ---
                # Eğer limit varsa ve bu oturumda çevrilen sayı limite ulaştıysa dur.
                if self.file_limit is not None and translated_count_session >= self.file_limit:
                    print(f"Belirlenen limit ({self.file_limit}) sayısına ulaşıldı.")
                    break
                # -----------------------------

                original_file_path = os.path.join(self.input_folder, file_name)
                translated_file_name = f"translated_{file_name}"
                translated_file_path = os.path.join(self.output_folder, translated_file_name)

                # Zaten çevrilmişse pas geç (Limitten düşmez, çünkü yeni çeviri yapılmadı)
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
                
                MAX_RETRIES = 3
                translated_text = None
                last_error = ""
                api_limit_hit = False
                retry_count = 0

                while retry_count < self.max_retries:
                    while self.is_paused and self.is_running:
                        time.sleep(0.5)
                        
                    if not self.is_running:
                        break

                    try:
                        response = self.model.generate_content(full_prompt)
                        
                        if response.prompt_feedback and response.prompt_feedback.block_reason:
                            raise Exception(f"İçerik engellendi: {response.prompt_feedback.block_reason.name}")

                        if not response.candidates or not response.candidates[0].content or not response.candidates[0].content.parts:
                            raise Exception("API'den boş yanıt alındı.")
                            
                        translated_text = response.candidates[0].content.parts[0].text
                        
                        if file_name in self.translation_errors:
                            del self.translation_errors[file_name]
                        break 
                    
                    except Exception as e:
                        last_error = str(e)
                        if ("500" in last_error) and retry_count < self.max_retries - 1:
                            retry_count += 1
                            wait_time = 2 ** retry_count
                            sleep_start = time.time()
                            while time.time() - sleep_start < wait_time:
                                if not self.is_running: break
                                time.sleep(0.5)
                        elif ("429" in last_error) or ("ResourceExhausted" in last_error):
                            self.error.emit("API sınırına ulaşıldı. Lütfen bekleyin veya API kullanımınızı kontrol edin.")
                            api_limit_hit = True
                            
                            # Update logs so we know this file failed. We shouldn't drop a text file if we don't have translated string
                            self.translation_errors[file_name] = f"Kota Aşıldı: {last_error}"
                            try:
                                with open(translated_file_path, 'w', encoding='utf-8') as f:
                                    f.write(f"Çeviri hatası (Kota aşıldı): {last_error}\n\nOrijinal Metin:\n{content[:500]}...")
                            except: pass
                            
                            break

                        else:
                            self.translation_errors[file_name] = f"Çeviri Hatası: {last_error}"
                            try:
                                with open(translated_file_path, 'w', encoding='utf-8') as f:
                                    f.write(f"Çeviri hatası: {last_error}\n\nOrijinal Metin:\n{content[:500]}...") 
                            except: pass
                            break
                
                # If API quota is exceeded, completely stop iterating through remaining files
                if api_limit_hit:
                    break
                    
                if not self.is_running:
                    break 

                if translated_text is not None:
                     with open(translated_file_path, 'w', encoding='utf-8') as f:
                        f.write(translated_text)
                     
                     # --- YENİ: Başarılı çeviri sayısını artır ---
                     translated_count_session += 1
                     # --------------------------------------------
                
                self.progress.emit(i + 1, total_files)

        except Exception as e:
            self.error.emit(f"Genel hata: {str(e)}")
        finally:
            try:
                with open(self.error_log_path, 'w', encoding='utf-8') as f:
                    json.dump(self.translation_errors, f, indent=4, ensure_ascii=False)
            except: pass

            self.finished.emit(self.shutdown_on_finish)