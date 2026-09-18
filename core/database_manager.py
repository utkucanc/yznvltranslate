"""
DatabaseManager — Projeler için SQLite veritabanı işlemlerini yönetir.
Klasör aramaları (os.listdir) yerine I/O işlemlerini hızlandırmayı sağlar.
"""
import sqlite3
import os
import time
from logger import app_logger

class DatabaseManager:
    """Proje dosyaları için SQLite veritabanı adaptörü."""
    
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.db_path = os.path.join(project_path, 'config', 'project_data.db')

    def db_exists(self) -> bool:
        """Veritabanının var olup olmadığını kontrol eder."""
        return os.path.exists(self.db_path)

    EXPECTED_COLUMNS = {
        "sort_key",
        "original_file_name",
        "original_file_path",
        "translated_file_name",
        "translated_file_path",
        "translation_status",
        "is_translated",
        "display_status"
    }

    def init_db(self):
        """Veritabanı bağlantısı açar, tablo yoksa oluşturur."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Files Tablosu
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                sort_key TEXT PRIMARY KEY,
                original_file_name TEXT,
                original_file_path TEXT,
                translated_file_name TEXT,
                translated_file_path TEXT,
                translation_status TEXT,
                is_translated BOOLEAN,
                display_status TEXT
            )
        ''')
        
        conn.commit()
        cursor.execute("PRAGMA table_info(files)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        if existing_columns != self.EXPECTED_COLUMNS:
            app_logger.warning("db şeması uyumsuz")
            cursor.execute("DROP TABLE files")
            conn.commit()
            conn.close()
            return self.init_db()
        conn.close()

    def get_all_files(self) -> list[dict]:
        """Tüm kayıtları 'sort_key' bazlı (doğal sayı okuma uyumlu olarak daha sonra list manager'da sortlanır) çeker."""
        if not self.db_exists():
            return []

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM files")
        rows = cursor.fetchall()
        conn.close()
        
        # SQLite satırlarını dict objesine dönüştür
        results = []
        for row in rows:
            results.append({
                "sort_key": row["sort_key"],
                "original_file_name": row["original_file_name"],
                "original_file_path": row["original_file_path"],
                "translated_file_name": row["translated_file_name"],
                "translated_file_path": row["translated_file_path"],
                "translation_status": row["translation_status"],
                "is_translated": bool(row["is_translated"]),
                "display_status": row["display_status"]
            })
            
        return results

    def upsert_files(self, files_data: list[dict]):
        """Liste halindeki dosya objelerini veritabanına yazar (varsa günceller, yoksa ekler)."""
        if not files_data:
            return

        self.init_db() # Tablo yoksa emin ol
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        insert_query = '''
            INSERT INTO files (
                sort_key, original_file_name, original_file_path,
                translated_file_name, translated_file_path, translation_status,
                is_translated, display_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(sort_key) DO UPDATE SET
                sort_key=excluded.sort_key,
                original_file_name=excluded.original_file_name,
                original_file_path=excluded.original_file_path,
                translated_file_name=excluded.translated_file_name,
                translated_file_path=excluded.translated_file_path,
                translation_status=excluded.translation_status,
                is_translated=excluded.is_translated,
                display_status=excluded.display_status
        '''

        # Veriyi demet(tuple) listesine çevirelim
        data_tuples = []
        for entry in files_data:
            data_tuples.append((
                entry.get("sort_key"),
                entry.get("original_file_name"),
                entry.get("original_file_path"),
                entry.get("translated_file_name"),
                entry.get("translated_file_path"),
                entry.get("translation_status"),
                entry.get("is_translated", False),
                entry.get("display_status")
            ))

        try:
            # executemany ile çok hızlı insert
            cursor.executemany(insert_query, data_tuples)
            conn.commit()
            app_logger.info(f"DB Upsert: {len(files_data)} dosya işlemi başarılı.")
        except Exception as e:
            app_logger.error(f"Veritabanı kayıt hatası (upsert_files): {e}")
            conn.rollback()
        finally:
            conn.close()

    def upsert_single_file(self, file_dict: dict):
        """Tek bir dosya kaydını veritabanına yazar (varsa günceller, yoksa ekler). Anlık çeviri sonuçlarını kaydetmek için kullanılır."""
        self.upsert_files([file_dict])

    def delete_file(self, sort_key: str) -> bool:
        """Verilen sort_key'e sahip dosyayı veritabanından siler."""
        if not self.db_exists():
            return False
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM files WHERE sort_key = ?", (sort_key,))
            conn.commit()
            deleted = cursor.rowcount > 0
            conn.close()
            app_logger.info(f"DB Delete: sort_key='{sort_key}' silindi.")
            return deleted
        except Exception as e:
            app_logger.error(f"Veritabanı silme hatası (delete_file): {e}")
            return False

    def sync_directory_to_db(self, legacy_file_list_manager) -> bool:
        """
        Klasik FileListManager vasıtasıyla tek seferliğine dizinleri tarayıp tüm veriyi SQLite'a geçirir.
        
        """
        try:
            # Geri dönüşümden kaçınmak ve yavaş taramayı tek kullanımlık koşturmak
            data = legacy_file_list_manager.get_file_list_data_legacy()
            files_data = data.get("sorted_entries", [])
            self.upsert_files(files_data)
            return True
        except Exception as e:
            app_logger.error(f"Aktarılma hatası (sync_directory_to_db): {e}")
            return False
