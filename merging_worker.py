import os
from PyQt6.QtCore import QObject, pyqtSignal
import datetime

class MergingWorker(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(str)
    progress = pyqtSignal(int, int)

    def __init__(self, files_to_merge, output_folder):
        super().__init__()
        self.files_to_merge = files_to_merge
        self.output_folder = output_folder
        self.is_running = True

    def run(self):
        if not self.files_to_merge:
            self.error.emit("Birleştirilecek dosya seçilmedi.")
            self.finished.emit()
            return

        # Çıktı dosya adı: mevcut tarih ve saat
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"merged_translation_{timestamp}.txt"
        output_filepath = os.path.join(self.output_folder, output_filename)

        try:
            with open(output_filepath, 'w', encoding='utf-8') as outfile:
                for i, file_path in enumerate(self.files_to_merge):
                    if not self.is_running:
                        self.error.emit("Birleştirme işlemi kullanıcı tarafından durduruldu.")
                        break

                    try:
                        with open(file_path, 'r', encoding='utf-8') as infile:
                            content = infile.read()
                            outfile.write("\n\n---BÖLÜM BAŞLANGICI---\n\n") # Bölümler arasına ayırıcı ekle
                            outfile.write(content)
                            
                    except Exception as e:
                        self.error.emit(f"'{os.path.basename(file_path)}' okunurken hata oluştu: {str(e)}")
                        # Hata olsa bile diğer dosyalara devam edilebilir
                    
                    self.progress.emit(i + 1, len(self.files_to_merge))
            
            if self.is_running: # Sadece işlem başarıyla tamamlandıysa bilgi ver
                # Son dosyanın sonunda ekstra ayırıcıyı kaldırabiliriz, basitlik için şimdilik bırakalım.
                pass

        except Exception as e:
            self.error.emit(f"Birleştirme işlemi sırasında genel hata oluştu: {str(e)}")
        finally:
            self.finished.emit()

    def stop(self):
        self.is_running = False
