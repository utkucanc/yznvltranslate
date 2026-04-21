from PyQt6.QtCore import QThread, pyqtSignal


class MLTerminologyWorker(QThread):
    """
    MLTerminologyExtractor'ı arka planda çalıştırmak için kullanılan işçi sınıfı.
    
    v2.4.0: Bölüm aralığı ve token limiti parametreleri eklendi.
    v2.4.1: finished_signal gerçekte işlenen son bölüm numarasını (int) taşıyor.
            Token limiti nedeniyle erken durulduğunda doğru bölüm kaydedilir.
    """
    progress_update = pyqtSignal(str)
    finished_signal = pyqtSignal(int)   # actual_end_chapter (gerçekte işlenen son bölüm)
    error_signal = pyqtSignal(str)

    def __init__(self, project_path: str, start_chapter: int | None = None,
                 end_chapter: int | None = None, max_tokens: int | None = None):
        """
        Args:
            project_path: Projenin kök dizini
            start_chapter: Dahil edilecek ilk bölüm sırası (1-tabanlı)
            end_chapter: Dahil edilecek son bölüm sırası (1-tabanlı)
            max_tokens: Maksimum token sayısı (None ise app_settings'den okunur)
        """
        super().__init__()
        self.project_path = project_path
        self.start_chapter = start_chapter
        self.end_chapter = end_chapter
        self.max_tokens = max_tokens

    def run(self):
        try:
            from core.workers.ml_terminology_extractor import MLTerminologyExtractor
            self.progress_update.emit("Terminoloji çıkarma arka planda başlatıldı...")
            extractor = MLTerminologyExtractor(self.project_path)
            actual_end = extractor.run(
                append=True,
                start_chapter=self.start_chapter,
                end_chapter=self.end_chapter,
                target_token_count=self.max_tokens
            )
            if actual_end is None:
                # run() None döndürdü → hata ya da boş metin
                self.error_signal.emit("Terminoloji çıkarma başarısız oldu veya işlenecek metin bulunamadı.")
                return

            self.progress_update.emit(f"Terminoloji başarıyla çıkartıldı. (Son bölüm: {actual_end})")
            self.finished_signal.emit(actual_end)

        except Exception as e:
            self.error_signal.emit(f"Hata: {e}")
