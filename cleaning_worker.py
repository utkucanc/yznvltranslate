import os
import json
from PyQt6.QtCore import pyqtSignal, QObject

# Temizlik fonksiyonunu içe aktarıyoruz
from temizlik import temizle_ve_kaydet 

class CleaningWorker(QObject):
    """
    Dosya temizleme işlemini arayüzü dondurmadan arka planda yürüten işçi sınıfı.
    """
    finished = pyqtSignal()
    error = pyqtSignal(str) # General error message for the worker
    progress = pyqtSignal(int, int) # Mevcut dosya ve toplam dosya sayısı için

    def __init__(self, file_paths: list[str], cleaning_folder: str):
        super().__init__()
        self.file_paths = file_paths
        self.cleaning_folder = cleaning_folder # Projenin trslt klasörü, hata logunu kaydetmek için
        self.is_running = True
        self.total_files = len(file_paths)
        self.processed_files = 0
        self.cleaning_errors = {} # Store errors for persistence

    def _save_errors_to_file(self):
        """Temizleme hatalarını JSON dosyasına kaydeder."""
        error_log_path = os.path.join(self.cleaning_folder, 'cleaning_errors.json')
        try:
            with open(error_log_path, 'w', encoding='utf-8') as f:
                json.dump(self.cleaning_errors, f, indent=4)
            print(f"Temizleme hataları '{error_log_path}' dosyasına kaydedildi.")
        except Exception as e:
            print(f"Hata: Temizleme hataları dosyaya kaydedilirken sorun oluştu: {e}")

    def run(self):
        """Temizleme işlemini başlatan ana fonksiyon."""
        self.cleaning_errors = {} # Reset errors for current run
        
        # Load existing errors at the start of the run to preserve them
        error_log_path = os.path.join(self.cleaning_folder, 'cleaning_errors.json')
        if os.path.exists(error_log_path):
            try:
                with open(error_log_path, 'r', encoding='utf-8') as f:
                    self.cleaning_errors = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"Uyarı: Mevcut temizleme hata dosyası '{error_log_path}' yüklenirken sorun oluştu: {e}. Yeni bir dosya oluşturulacak.")
                self.cleaning_errors = {}
            except Exception as e:
                print(f"Uyarı: Mevcut temizleme hata dosyası '{error_log_path}' yüklenirken genel hata: {e}. Yeni bir dosya oluşturulacak.")
                self.cleaning_errors = {}

        try:
            for i, file_path in enumerate(self.file_paths):
                if not self.is_running:
                    print("Temizleme işçisi durdurma isteği aldı, döngüden çıkılıyor.")
                    break

                file_name = os.path.basename(file_path)
                
                # Check if this file was previously cleaned successfully, or if there's a specific error
                # If it's in errors, we should re-attempt to clean it.
                if file_name not in self.cleaning_errors:
                    print(f"'{file_name}' temizleniyor...")
                    success, message = temizle_ve_kaydet(file_path)

                    if success:
                        # Remove from errors if it was previously failed and now succeeded
                        if file_name in self.cleaning_errors:
                            del self.cleaning_errors[file_name]
                        print(f"'{file_name}' başarıyla temizlendi: {message}")
                    else:
                        self.cleaning_errors[file_name] = message
                        print(f"Hata: '{file_name}' temizlenirken sorun oluştu: {message}")
                else:
                    print(f"'{file_name}' zaten hata geçmişinde. Tekrar deneniyor...")
                    success, message = temizle_ve_kaydet(file_path)
                    if success:
                        if file_name in self.cleaning_errors:
                            del self.cleaning_errors[file_name]
                        print(f"'{file_name}' başarıyla temizlendi: {message}")
                    else:
                        self.cleaning_errors[file_name] = message
                        print(f"Hata: '{file_name}' temizlenirken sorun oluştu: {message}")


                self.processed_files += 1
                self.progress.emit(self.processed_files, self.total_files)
                self._save_errors_to_file() # Save errors after processing each file

        except Exception as e:
            self.error.emit(str(e))
        finally:
            self._save_errors_to_file() # Final save of errors
            self.finished.emit()
            print("Temizleme işçisi tamamlandı/durduruldu.")

    def stop(self):
        """Temizleme döngüsünü durdurur."""
        self.is_running = False
        print("Temizleme işçisi durdurma isteği aldı.")
