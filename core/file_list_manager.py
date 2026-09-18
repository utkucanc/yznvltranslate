"""
FileListManager — Proje içerisindeki dizinleri tarayarak indirilen, çevrilen ve birleştirilen dosyaların analizini yapar. UI'dan bağımsızdır.
"""
import os
import json
import time

from core.utils import format_file_size, natural_sort_key
from core.workers.token_counter import load_token_data
from logger import app_logger
from core.path_resolver import get_subfolder_path

class FileListManager:
    """Projedeki dosyaları tarar, eşleştirir ve durumlarını derler."""
    
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.config_folder = get_subfolder_path(project_path, 'config')
        self.download_folder = get_subfolder_path(project_path, 'download')
        self.translated_folder = get_subfolder_path(project_path, 'translate')
        self.completed_folder = get_subfolder_path(project_path, 'completed')

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
        Geriye dönük uyumluluk veya Aktarma senaryoları için kullanılır.
        """
        translation_errors = self._load_json_silent(os.path.join(self.translated_folder, 'translation_errors.json'))

        file_data_map = {}
        # 1. Downloaded (Orijinal) Dosyalar
        if os.path.exists(self.download_folder):
            dwnld_files = sorted([f for f in os.listdir(self.download_folder) if f.endswith('.txt')])
            for file_name in dwnld_files:
                original_file_base = file_name.replace(".txt", "")
                
                file_path = os.path.join(self.download_folder, file_name)
                file_data_map[original_file_base] = {
                    "original_file_name": file_name,
                    "original_file_path": file_path,
                    "translated_file_name": "",
                    "translated_file_path": "",
                    "translation_status": "Çevrilmedi",
                    "is_translated": False,
                    "sort_key": original_file_base,
                    "display_status": ""
                }
                if file_name in translation_errors:
                    file_data_map[original_file_base]["translation_status"] = f"Hata: {translation_errors[file_name]}"
            
            
        else:
            app_logger.debug(f"download klasörü bulunamadı: {self.download_folder}")

        # 2. Translated (Çevrilen) Dosyalar
        if os.path.exists(self.translated_folder):
            trslt_files = sorted([f for f in os.listdir(self.translated_folder) if f.startswith('translated_') and f.endswith('.txt')])
            
            for translated_file_name in trslt_files:
                original_file_name_candidate = translated_file_name.replace("translated_", "")
                original_file_base = original_file_name_candidate.replace(".txt", "")

                

                if original_file_base in file_data_map:
                    entry = file_data_map[original_file_base]
                    entry["translated_file_name"] = translated_file_name
                    entry["translated_file_path"] = os.path.join(self.translated_folder, translated_file_name)
                    entry["is_translated"] = True

                    if original_file_name_candidate in translation_errors:
                        entry["translation_status"] = f"Hata: {translation_errors[original_file_name_candidate]}"
                    else:
                        entry["translation_status"] = "Çevrildi"

                else:
                    translated_file_path = os.path.join(self.translated_folder, translated_file_name)
                    file_data_map[original_file_base] = {
                        "original_file_name": "Orijinali Yok",
                        "original_file_path": "",
                        "translated_file_name": translated_file_name,
                        "translated_file_path": translated_file_path,
                        "translation_status": "Orijinali Yok",
                        "is_translated": True,
                        "sort_key": original_file_base,
                        "display_status": ""
                    }
        else:
            app_logger.debug(f"translated klasörü bulunamadı: {self.translated_folder}")

        # 3. Completed (Birleştirilmiş) Dosyalar
        if os.path.exists(self.completed_folder):
            cmplt_files = sorted([f for f in os.listdir(self.completed_folder) if f.endswith(('.txt', '.json', '.epub'))])
            
            for file_name in cmplt_files:
                merged_file_base = f"merged_{file_name.replace('.txt', '').replace('.json', '').replace('.epub', '')}"
                file_path = os.path.join(self.completed_folder, file_name)
                file_data_map[merged_file_base] = {
                    "original_file_name": "N/A",
                    "original_file_path": "",
                    "translated_file_name": file_name,
                    "translated_file_path": file_path,
                    "translation_status": "Birleştirildi",
                    "is_translated": False,
                    "sort_key": merged_file_base,
                    "display_status": ""
                }
        else:
            app_logger.debug(f"completed klasörü bulunamadı: {self.completed_folder}")

        # 4. Durumları birleştir
        for key, entry in file_data_map.items():
            final_status = ""
            if entry["translation_status"] == "Birleştirildi":
                final_status = "Birleştirildi"
            elif entry["original_file_name"] == "Orijinali Yok":
                final_status = f"Orijinali Yok, {entry['translation_status']}"
            elif entry["translation_status"].startswith("Hata:"):
                final_status = entry["translation_status"]
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
        }

    def force_rescan_and_sync_db(self) -> dict:
        """
        Dizinleri canlı olarak (os.listdir) tarar, elde edilen güncel durum verisini 
        SQLite veritabanına yazar ve güncel veri sözlüğünü döner.
        Yalnızca yenileme butonları tetiklediğinde kullanılır.
        """
        from core.database_manager import DatabaseManager
        data = self.get_file_list_data_legacy()
        sorted_entries = data.get("sorted_entries", [])
        
        db_mgr = DatabaseManager(self.project_path)
        db_mgr.upsert_files(sorted_entries)
        return data

    def get_file_list_data(self) -> dict:
        """
        Öncelikli olarak veritabanını kullanmayı dener.
        Eğer projede (.db) dosyası bulunmuyorsa doğrudan 'legacy' metodunu çalıştırır.
        """
        from core.database_manager import DatabaseManager
        db_mgr = DatabaseManager(self.project_path)
        
        # Geriye dönük uyumluluk: DB yoksa, yavaş modda diskten oku ve DB'ye eşitle
        if not db_mgr.db_exists():
            data = self.get_file_list_data_legacy()
            db_mgr.upsert_files(data.get("sorted_entries", []))
            return data
        
        # Zeki Eşitleme ve Okuma: DB var. SQLite'dan verileri hızlıca çek.
        db_entries = db_mgr.get_all_files()
        
        from core.utils import natural_sort_key
        sorted_entries = sorted(
            db_entries,
            key=lambda x: (
                0 if x.get("translation_status") == "Birleştirildi" else 1,
                natural_sort_key(x["sort_key"])
            )
        )
        
        return {
            "sorted_entries": sorted_entries,
        }
