"""
FileListManager — Proje içerisindeki dizinleri tarayarak indirilen, çevrilen ve birleştirilen dosyaların analizini yapar. UI'dan bağımsızdır.
"""
import os
import json
import time

from core.utils import format_file_size, natural_sort_key
from core.workers.token_counter import load_token_data
from logger import app_logger

class FileListManager:
    """Projedeki dosyaları tarar, eşleştirir ve durumlarını derler."""
    
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.config_folder = os.path.join(project_path, 'config')
        self.download_folder = os.path.join(project_path, 'dwnld')
        self.translated_folder = os.path.join(project_path, 'trslt')
        self.completed_folder = os.path.join(project_path, 'cmplt')

    def _load_json_silent(self, filepath: str) -> dict:
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def get_file_list_data_legacy(self) -> dict:
        """
        Dizinleri eski (os.listdir & os.stat) yöntemiyle tarar ve veri sözlüğünü döner.
        Geriye dönük uyumluluk veya Migration senaryoları için kullanılır.
        {
          "sorted_entries": [ ... dosyalar ... ],
          "project_token_cache": { ... cache verileri ... }
        }
        """
        token_cache = load_token_data(self.config_folder)
        translation_errors = self._load_json_silent(os.path.join(self.translated_folder, 'translation_errors.json'))
        cleaning_errors = self._load_json_silent(os.path.join(self.translated_folder, 'cleaning_errors.json'))

        file_data_map = {}
        # 1. Downloaded (Orijinal) Dosyalar
        if os.path.exists(self.download_folder):
            dwnld_files = sorted([f for f in os.listdir(self.download_folder) if f.endswith('.txt')])
            for file_name in dwnld_files:
                original_file_base = file_name.replace(".txt", "")
                file_path = os.path.join(self.download_folder, file_name)
                try:
                    file_stat = os.stat(file_path)
                    creation_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(file_stat.st_ctime))
                    file_size = format_file_size(file_stat.st_size)
                except Exception:
                    creation_time, file_size = "Bilinmiyor", "Bilinmiyor"

                cached_tokens_data = token_cache.get("file_token_data", {}).get(file_name, {})
                original_token_count = cached_tokens_data.get("original_tokens", "Hesaplanmadı")

                file_data_map[original_file_base] = {
                    "original_file_name": file_name,
                    "original_file_path": file_path,
                    "original_creation_time": creation_time,
                    "original_file_size": file_size,
                    "translated_file_name": "",
                    "translated_file_path": "",
                    "translation_status": "Çevrilmedi",
                    "cleaning_status": "Temizlenmedi",
                    "is_translated": False,
                    "is_cleaned": False,
                    "sort_key": original_file_base,
                    "original_token_count": original_token_count,
                    "translated_token_count": "Yok",
                    "display_status": ""
                }
                if file_name in translation_errors:
                    file_data_map[original_file_base]["translation_status"] = f"Hata: {translation_errors[file_name]}"
                if file_name in cleaning_errors:
                    file_data_map[original_file_base]["cleaning_status"] = f"Hata: {cleaning_errors[file_name]}"

        # 2. Translated (Çevrilen) Dosyalar
        if os.path.exists(self.translated_folder):
            trslt_files = sorted([f for f in os.listdir(self.translated_folder) if f.startswith('translated_') and f.endswith('.txt')])
            for translated_file_name in trslt_files:
                original_file_name_candidate = translated_file_name.replace("translated_", "")
                original_file_base = original_file_name_candidate.replace(".txt", "")

                cached_tokens_data = token_cache.get("file_token_data", {}).get(translated_file_name, {})
                translated_token_count = cached_tokens_data.get("translated_tokens", "Hesaplanmadı")

                if original_file_base in file_data_map:
                    entry = file_data_map[original_file_base]
                    entry["translated_file_name"] = translated_file_name
                    entry["translated_file_path"] = os.path.join(self.translated_folder, translated_file_name)
                    entry["is_translated"] = True
                    entry["translated_token_count"] = translated_token_count

                    if original_file_name_candidate in translation_errors:
                        entry["translation_status"] = f"Hata: {translation_errors[original_file_name_candidate]}"
                    else:
                        entry["translation_status"] = "Çevrildi"

                    if translated_file_name in cleaning_errors:
                        entry["cleaning_status"] = f"Hata: {cleaning_errors[translated_file_name]}"
                else:
                    translated_file_path = os.path.join(self.translated_folder, translated_file_name)
                    try:
                        file_stat = os.stat(translated_file_path)
                        creation_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(file_stat.st_ctime))
                        file_size = format_file_size(file_stat.st_size)
                    except Exception:
                        creation_time, file_size = "Bilinmiyor", "Bilinmiyor"

                    file_data_map[original_file_base] = {
                        "original_file_name": "Orijinali Yok",
                        "original_file_path": "",
                        "original_creation_time": creation_time,
                        "original_file_size": file_size,
                        "translated_file_name": translated_file_name,
                        "translated_file_path": translated_file_path,
                        "translation_status": "Orijinali Yok",
                        "cleaning_status": "Temizlenmedi",
                        "is_translated": True,
                        "is_cleaned": False,
                        "sort_key": original_file_base,
                        "original_token_count": "Yok",
                        "translated_token_count": translated_token_count,
                        "display_status": ""
                    }
                    if translated_file_name in cleaning_errors:
                        file_data_map[original_file_base]["cleaning_status"] = f"Hata: {cleaning_errors[translated_file_name]}"

        # 3. Completed (Birleştirilmiş) Dosyalar
        if os.path.exists(self.completed_folder):
            cmplt_files = sorted([f for f in os.listdir(self.completed_folder) if f.endswith(('.txt', '.json', '.epub'))])
            for file_name in cmplt_files:
                merged_file_base = f"merged_{file_name.replace('.txt', '').replace('.json', '').replace('.epub', '')}"
                file_path = os.path.join(self.completed_folder, file_name)

                try:
                    file_stat = os.stat(file_path)
                    creation_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(file_stat.st_ctime))
                    file_size = format_file_size(file_stat.st_size)
                except Exception:
                    creation_time, file_size = "Bilinmiyor", "Bilinmiyor"

                cached_tokens_data = token_cache.get("file_token_data", {}).get(file_name, {})
                merged_token_count = cached_tokens_data.get("merged_tokens", "Hesaplanmadı")

                file_data_map[merged_file_base] = {
                    "original_file_name": "N/A",
                    "original_file_path": "",
                    "original_creation_time": creation_time,
                    "original_file_size": file_size,
                    "translated_file_name": file_name,
                    "translated_file_path": file_path,
                    "translation_status": "Birleştirildi",
                    "cleaning_status": "N/A",
                    "is_translated": False,
                    "is_cleaned": False,
                    "sort_key": merged_file_base,
                    "original_token_count": "N/A",
                    "translated_token_count": merged_token_count,
                    "display_status": ""
                }

        # 4. Durumları birleştir
        for key, entry in file_data_map.items():
            final_status = ""
            if entry["translation_status"] == "Birleştirildi":
                final_status = "Birleştirildi"
            elif entry["original_file_name"] == "Orijinali Yok":
                final_status = f"Orijinali Yok, {entry['translation_status']}"
            elif entry["translation_status"].startswith("Hata:"):
                final_status = entry["translation_status"]
            elif entry["cleaning_status"].startswith("Hata:"):
                final_status = entry["cleaning_status"]
            elif entry["is_translated"]:
                final_status = entry["translation_status"]
            else:
                final_status = "İndirildi"

            entry["display_status"] = final_status

        sorted_entries = sorted(
            file_data_map.values(),
            key=lambda x: (
                # Birleştirilmiş dosyalar (cmplt) en başa
                0 if x["translation_status"] == "Birleştirildi" else 1,
                natural_sort_key(x["sort_key"])
            )
        )
        app_logger.info(f"FileListManager: {len(sorted_entries)} dosya bulundu ve işlendi (Legacy Yöntem).")
        return {
            "sorted_entries": sorted_entries,
            "project_token_cache": token_cache
        }

    def get_file_list_data(self) -> dict:
        """
        Öncelikli olarak veritabanını kullanmayı dener.
        Eğer projede (.db) dosyası bulunmuyorsa doğrudan 'legacy' metodunu çalıştırır.
        """
        from core.database_manager import DatabaseManager
        db_mgr = DatabaseManager(self.project_path)
        
        # Geriye dönük uyumluluk: DB yoksa, yavaş modda diskten oku
        if not db_mgr.db_exists():
            return self.get_file_list_data_legacy()
        
        # Zeki Eşitleme ve Okuma: DB var.
        # SQLite'dan verileri çok hızlı çek
        db_entries = db_mgr.get_all_files()
        
        # NOT: Eğer yeni indirme, silinme vs. varsa burada hafif bir klasör sayısı
        # kontrolü (Smart Sync) yapılabilir, eksik dosyalar SQLite'a atılır.
        # Şimdilik TranslationWorker vb. SQLite'ı direkt besleyeceği için SELECT yeterlidir.
        
        token_cache = load_token_data(self.config_folder)
        # Sort işlemi (veritabanından çekerken her ihtimale karşı UI için sıralanır)
        from core.utils import natural_sort_key
        sorted_entries = sorted(
            db_entries,
            key=lambda x: (
                # Birleştirilmiş dosyalar (cmplt) en başa
                0 if x.get("translation_status") == "Birleştirildi" else 1,
                natural_sort_key(x["sort_key"])
            )
        )
        
        return {
            "sorted_entries": sorted_entries,
            "project_token_cache": token_cache
        }
