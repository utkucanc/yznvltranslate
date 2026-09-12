from core.path_resolver import get_subfolder_path
import os
import copy
from PyQt6.QtCore import QObject, pyqtSignal

from logger import app_logger
from core.workers.token_counter import count_tokens_in_file

class TokenCountWorker(QObject):
    finished = pyqtSignal(dict) # Tüm token verilerini döndür
    progress = pyqtSignal(int, int) # Current file index, total files
    error = pyqtSignal(str)

    def __init__(self, project_path, api_key, current_token_cache, model_version, selected_files=None, endpoint_id=None):
        super().__init__()
        self.project_path = project_path
        self.api_key = api_key
        self.is_running = True
        self.current_token_cache = current_token_cache # Mevcut önbellek (dict)
        self.model_version = model_version
        self.selected_files = selected_files
        self.endpoint_id = endpoint_id
        # Mevcut önbellekten derin kopya al — önceki token kayıtlarını korumak için
        if current_token_cache and "file_token_data" in current_token_cache:
            self.token_data_to_save = copy.deepcopy(current_token_cache)
        else:
            self.token_data_to_save = {"file_token_data": {}, "total_original_tokens": 0, "total_translated_tokens": 0, "total_combined_tokens": 0}


    def run(self):
        app_logger.info(f"TokenCountWorker başlatıldı. Proje: {self.project_path}")
        original_folder = get_subfolder_path(self.project_path, 'download')
        translated_folder = get_subfolder_path(self.project_path, 'translate')
        completed_folder = get_subfolder_path(self.project_path, 'completed')

        total_original_tokens_sum = 0
        total_translated_tokens_sum = 0
        
        # Dosya listelerini oluştur
        original_files = sorted([f for f in os.listdir(original_folder) if f.endswith('.txt')]) if os.path.exists(original_folder) else []
        translated_files = sorted([f for f in os.listdir(translated_folder) if f.startswith('translated_') and f.endswith('.txt')]) if os.path.exists(translated_folder) else []
        merged_files = sorted([f for f in os.listdir(completed_folder) if f.startswith('merged_') and f.endswith('.txt')]) if os.path.exists(completed_folder) else []

        all_relevant_files = [] # {filename, path, type (original/translated/merged)}
        for f in original_files:
            if self.selected_files and f not in self.selected_files: continue
            all_relevant_files.append({'name': f, 'path': os.path.join(original_folder, f), 'type': 'original'})
        for f in translated_files:
            if self.selected_files and f not in self.selected_files: continue
            all_relevant_files.append({'name': f, 'path': os.path.join(translated_folder, f), 'type': 'translated'})
        for f in merged_files:
            if self.selected_files and f not in self.selected_files: continue
            all_relevant_files.append({'name': f, 'path': os.path.join(completed_folder, f), 'type': 'merged'})
        
        total_files_to_check = len(all_relevant_files)
        processed_count = 0
        app_logger.info(f"Token sayılacak dosya sayısı: {total_files_to_check}")

        # Her bir dosyayı işle
        for file_info in all_relevant_files:
            if not self.is_running: 
                app_logger.info("TokenCountWorker durduruldu, döngüden çıkılıyor.")
                break

            file_name = file_info['name']
            file_path = file_info['path']
            file_type = file_info['type']
            app_logger.debug(f"[{processed_count+1}/{total_files_to_check}] İşleniyor: {file_name} ({file_type})")
            
            # Önbellekte dosya verisini ara
            cached_data = self.current_token_cache.get("file_token_data", {}).get(file_name)
            
            current_mtime = os.path.getmtime(file_path) # Mevcut değiştirme zamanı
            
            token_count = None
            should_recount = True

            if cached_data:
                # Cache'de mtime kontrolü yap
                if file_type == 'original' and cached_data.get('original_mtime') == current_mtime:
                    token_count = cached_data.get('original_tokens')
                    should_recount = False
                elif file_type == 'translated' and cached_data.get('translated_mtime') == current_mtime:
                    token_count = cached_data.get('translated_tokens')
                    should_recount = False
                elif file_type == 'merged' and cached_data.get('merged_mtime') == current_mtime:
                    token_count = cached_data.get('merged_tokens')
                    should_recount = False

                if not should_recount:
                    app_logger.debug(f"'{file_name}' için önbellekteki değer kullanılıyor: {token_count}")
            
            if should_recount:
                app_logger.debug(f"'{file_name}' için API çağrısı yapılıyor...")
                tokens, err = count_tokens_in_file(file_path, self.api_key, self.model_version, endpoint_id=self.endpoint_id)
                if tokens is not None:
                    token_count = tokens
                    app_logger.debug(f"'{file_name}' token sayımı tamamlandı: {tokens}")
                else:
                    app_logger.error(f"Token sayım hatası ({file_name}): {err}")
            
            # Sonuçları işçi verisine kaydet
            if file_name not in self.token_data_to_save["file_token_data"]:
                self.token_data_to_save["file_token_data"][file_name] = {
                    "original_tokens": None, "original_mtime": None,
                    "translated_tokens": None, "translated_mtime": None,
                    "merged_tokens": None, "merged_mtime": None
                }
            
            if file_type == 'original':
                self.token_data_to_save["file_token_data"][file_name]["original_tokens"] = token_count
                self.token_data_to_save["file_token_data"][file_name]["original_mtime"] = current_mtime
                if token_count is not None:
                    total_original_tokens_sum += token_count
            elif file_type == 'translated':
                self.token_data_to_save["file_token_data"][file_name]["translated_tokens"] = token_count
                self.token_data_to_save["file_token_data"][file_name]["translated_mtime"] = current_mtime
                if token_count is not None:
                    total_translated_tokens_sum += token_count
            elif file_type == 'merged':
                self.token_data_to_save["file_token_data"][file_name]["merged_tokens"] = token_count
                self.token_data_to_save["file_token_data"][file_name]["merged_mtime"] = current_mtime

            processed_count += 1
            self.progress.emit(processed_count, total_files_to_check)
        
        app_logger.info("Tüm dosyalar işlendi. finished sinyali yayınlanıyor...")

        # Toplam tokenleri TÜM kayıtlardan yeniden hesapla (sadece seçili dosyalar değil)
        # Böylece önceki sayımlar dahil doğru genel toplam elde edilir
        grand_original = 0
        grand_translated = 0
        for fname, fdata in self.token_data_to_save["file_token_data"].items():
            orig = fdata.get("original_tokens")
            trans = fdata.get("translated_tokens")
            if orig is not None:
                grand_original += orig
            if trans is not None:
                grand_translated += trans

        self.token_data_to_save["total_original_tokens"] = grand_original
        self.token_data_to_save["total_translated_tokens"] = grand_translated
        self.token_data_to_save["total_combined_tokens"] = grand_original + grand_translated

        self.finished.emit(self.token_data_to_save)
        app_logger.info("finished sinyali yayınlandı.")
    
    def stop(self):
        self.is_running = False
