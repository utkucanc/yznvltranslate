import os
import threading
import configparser
from PyQt6.QtCore import QThread, pyqtSignal

_config_save_lock = threading.Lock()

class MLTerminologyWorker(QThread):
    """
    MLTerminologyExtractor'ı arka planda çalıştırmak için kullanılan işçi sınıfı.
    
    v2.4.0: Bölüm aralığı ve token limiti parametreleri eklendi.
    v2.4.1: finished_signal gerçekte işlenen son bölüm numarasını (int) taşıyor.
            Token limiti nedeniyle erken durulduğunda doğru bölüm kaydedilir.
    v2.4.2: extract_all (Tamamının terminolojisi) ve async_enabled (Paralel çıkarma) desteği eklendi.
    """
    progress_update = pyqtSignal(str)
    finished_signal = pyqtSignal(int)   # actual_end_chapter (gerçekte işlenen son bölüm)
    error_signal = pyqtSignal(str)

    def __init__(self, project_path: str, start_chapter: int | None = None,
                 end_chapter: int | None = None, max_tokens: int | None = None,
                 extract_all: bool = False, async_enabled: bool = False,
                 async_threads: int = 3):
        """
        Args:
            project_path: Projenin kök dizini
            start_chapter: Dahil edilecek ilk bölüm sırası (1-tabanlı)
            end_chapter: Dahil edilecek son bölüm sırası (1-tabanlı)
            max_tokens: Maksimum token sayısı (None ise app_settings'den okunur)
            extract_all: Tüm bölümleri parça parça sonuna kadar çıkar
            async_enabled: Paralel asenkron çıkarma
            async_threads: Paralel thread/worker sayısı
        """
        super().__init__()
        self.project_path = project_path
        self.start_chapter = start_chapter
        self.end_chapter = end_chapter
        self.max_tokens = max_tokens
        self.extract_all = extract_all
        self.async_enabled = async_enabled
        self.async_threads = async_threads
        self._is_running = True

    def stop(self):
        self._is_running = False

    def _save_last_operation(self, start_ch: int, end_ch: int):
        """Son terminoloji işleminin bölüm numaralarını proje config.ini'sine yazar."""
        config_path = os.path.join(self.project_path, "config", "config.ini")
        cfg = configparser.ConfigParser()
        with _config_save_lock:
            try:
                if os.path.exists(config_path):
                    cfg.read(config_path, encoding="utf-8")
                if "TerminologyOp" not in cfg:
                    cfg["TerminologyOp"] = {}
                cfg["TerminologyOp"]["last_start_chapter"] = str(start_ch)
                cfg["TerminologyOp"]["last_end_chapter"] = str(end_ch)
                with open(config_path, "w", encoding="utf-8") as f:
                    cfg.write(f)
            except Exception as e:
                from logger import app_logger
                app_logger.warning(f"Terminoloji bölüm bilgisi config.ini'ye yazılamadı: {e}")

    def _get_chunk_ranges(self) -> list[tuple[int, int]]:
        dwnld_dir = os.path.join(self.project_path, "dwnld")
        if not os.path.exists(dwnld_dir):
            return []
        all_files = sorted([f for f in os.listdir(dwnld_dir) if f.endswith(".txt")])
        
        start_chapter = self.start_chapter or 1
        end_chapter = self.end_chapter or len(all_files)
        
        s = (start_chapter - 1) if start_chapter >= 1 else 0
        e = end_chapter
        dwnld_files = all_files[s:e]
        
        try:
            from core.workers.token_counter import get_local_token_count_approx
        except ImportError:
            def get_local_token_count_approx(text):
                return int(len(text) / 2.5)

        max_tokens = self.max_tokens
        if max_tokens is None:
            try:
                settings_path = os.path.join(os.getcwd(), "AppConfigs", "app_settings.json")
                if os.path.exists(settings_path):
                    import json
                    with open(settings_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    max_tokens = int(data.get("ml_max_tokens", 450000))
            except Exception:
                max_tokens = 450000

        chunks = []
        current_chunk_files = []
        current_tokens = 0
        upper_limit = max_tokens * 1.05
        
        chunk_start_idx = s
        for i, file in enumerate(dwnld_files):
            file_path = os.path.join(dwnld_dir, file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception:
                content = ""
            
            file_tokens = get_local_token_count_approx(content)
            if current_tokens + file_tokens > upper_limit and current_chunk_files:
                # Close current chunk
                chunk_end_idx = s + i
                chunks.append((chunk_start_idx + 1, chunk_end_idx))
                # Start next chunk
                chunk_start_idx = s + i
                current_chunk_files = [file]
                current_tokens = file_tokens
            else:
                current_chunk_files.append(file)
                current_tokens += file_tokens
                
        if current_chunk_files:
            chunk_end_idx = s + len(dwnld_files)
            chunks.append((chunk_start_idx + 1, chunk_end_idx))
            
        return chunks

    def run(self):
        try:
            from core.workers.ml_terminology_extractor import MLTerminologyExtractor
            
            if not self.extract_all:
                self.progress_update.emit("Terminoloji çıkarma arka planda başlatıldı...")
                extractor = MLTerminologyExtractor(self.project_path)
                actual_end = extractor.run(
                    append=True,
                    start_chapter=self.start_chapter,
                    end_chapter=self.end_chapter,
                    target_token_count=self.max_tokens
                )
                if actual_end is None:
                    self.error_signal.emit("Terminoloji çıkarma başarısız oldu veya işlenecek metin bulunamadı.")
                    return
                self._save_last_operation(self.start_chapter, actual_end)
                self.progress_update.emit(f"Terminoloji başarıyla çıkartıldı. (Son bölüm: {actual_end})")
                self.finished_signal.emit(actual_end)
                return

            # extract_all is True
            chunks = self._get_chunk_ranges()
            if not chunks:
                self.error_signal.emit("İşlenecek bölüm aralığı bulunamadı.")
                return

            self.progress_update.emit(f"Toplam {len(chunks)} parça halinde terminoloji çıkartılacak...")
            
            actual_ends = []
            
            if self.async_enabled:
                import concurrent.futures
                self.progress_update.emit(f"Asenkron terminoloji çıkarma başlatılıyor ({self.async_threads} paralel işlem)...")
                
                completed_chunks = 0
                total_chunks = len(chunks)
                progress_lock = threading.Lock()

                def process_chunk(chunk_start, chunk_end):
                    if not self._is_running:
                        return None
                    extractor = MLTerminologyExtractor(self.project_path)
                    res = extractor.run(
                        append=True,
                        start_chapter=chunk_start,
                        end_chapter=chunk_end,
                        target_token_count=self.max_tokens
                    )
                    if res is not None:
                        self._save_last_operation(chunk_start, res)
                        nonlocal completed_chunks
                        with progress_lock:
                            completed_chunks += 1
                            self.progress_update.emit(f"İlerleme: {completed_chunks}/{total_chunks} parça tamamlandı. (Bölüm: {res})")
                    return res

                with concurrent.futures.ThreadPoolExecutor(max_workers=self.async_threads) as executor:
                    futures = [executor.submit(process_chunk, c_start, c_end) for c_start, c_end in chunks]
                    for fut in concurrent.futures.as_completed(futures):
                        if not self._is_running:
                            break
                        try:
                            res = fut.result()
                            if res is not None:
                                actual_ends.append(res)
                        except Exception as e:
                            from logger import app_logger
                            app_logger.error(f"Paralel terminoloji çıkarma hatası: {e}")
            else:
                # Sequential mode
                for c_start, c_end in chunks:
                    if not self._is_running:
                        break
                    self.progress_update.emit(f"Bölümler {c_start} - {c_end} işleniyor...")
                    extractor = MLTerminologyExtractor(self.project_path)
                    res = extractor.run(
                        append=True,
                        start_chapter=c_start,
                        end_chapter=c_end,
                        target_token_count=self.max_tokens
                    )
                    if res is not None:
                        actual_ends.append(res)
                        self._save_last_operation(c_start, res)
                    else:
                        self.progress_update.emit(f"Uyarı: {c_start} - {c_end} aralığı işlenemedi.")

            if not self._is_running:
                self.progress_update.emit("Terminoloji çıkarma işlemi kullanıcı tarafından durduruldu.")
                return

            if not actual_ends:
                self.error_signal.emit("Hiçbir bölümden terminoloji çıkartılamadı.")
                return

            final_end = max(actual_ends)
            self.progress_update.emit(f"Tüm bölümler için terminoloji başarıyla çıkartıldı. (Son bölüm: {final_end})")
            self.finished_signal.emit(final_end)

        except Exception as e:
            self.error_signal.emit(f"Hata: {e}")
