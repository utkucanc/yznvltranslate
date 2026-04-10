import os
import json
import re
import datetime
from PyQt6.QtCore import QThread, pyqtSignal
from logger import app_logger

class JsonOutputWorker(QThread):
    finished = pyqtSignal()
    error = pyqtSignal(str)
    progress = pyqtSignal(int, int)
    success = pyqtSignal(str)

    def __init__(self, selected_files, project_path, project_name):
        super().__init__()
        self.selected_files = selected_files
        self.project_path = project_path
        self.project_name = project_name
        self.is_running = True

    def run(self):
        if not self.selected_files:
            self.error.emit("İşlenecek dosya seçilmedi.")
            app_logger.error("İşlenecek dosya seçilmedi.")
            self.finished.emit()
            return
        app_logger.info(f"JSON oluşturma işlemi başlatıldı. Proje: {self.project_name}")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        cmplt_folder = os.path.join(self.project_path, "cmplt")
        os.makedirs(cmplt_folder, exist_ok=True)
        output_filepath = os.path.join(cmplt_folder, "output_"+timestamp+".json")
        json_data = []

        try:
            total_files = len(self.selected_files)
            for i, file_path in enumerate(self.selected_files):
                if not self.is_running:
                    self.error.emit("İşlem kullanıcı tarafından durduruldu.")
                    app_logger.error("İşlem kullanıcı tarafından durduruldu.")
                    break

                try:
                    with open(file_path, 'r', encoding='utf-8') as infile:
                        content = infile.read()
                        
                    # Extract title
                    lines = content.split('\n')
                    first_line = lines[0].strip() if lines else ""
                    content_title = ""

                    # Extract chapter number
                    filename = os.path.basename(file_path)
                    match = re.search(r'\d+', filename)
                    chapter_no = ""
                    if match:
                        chapter_no = str(int(match.group(0))) # Baştaki sıfırları atar

                    # İlk 3 kelimede "Bölüm" kelimesini ara
                    words = first_line.split()[:3]
                    if any("Bölüm" in word or "bölüm" in word.lower() for word in words):
                        content_title = first_line      
                    else:
                        content_title = "Bölüm " + chapter_no

                    # Append to json array
                    json_obj = {
                        "title": content_title,
                        "chapterNo": chapter_no,
                        "content": content,
                        "url": "NONE",
                        "novelTitle": self.project_name,
                        "originalTitle": content_title,
                        "originalContentLength": None,
                        "translatedContentLength": None
                    }
                    
                    json_data.append(json_obj)
                        
                except Exception as e:
                    self.error.emit(f"'{os.path.basename(file_path)}' okunurken hata oluştu: {str(e)}")
                    app_logger.error(f"'{os.path.basename(file_path)}' okunurken hata oluştu: {str(e)}")
                
                self.progress.emit(i + 1, total_files)

            if self.is_running:
                with open(output_filepath, 'w', encoding='utf-8') as outfile:
                    json.dump(json_data, outfile, ensure_ascii=False, indent=4)
                self.success.emit(f"JSON dosyası başarıyla kaydedildi:\n{output_filepath}")
                app_logger.info(f"JSON dosyası başarıyla kaydedildi: {output_filepath}")

        except Exception as e:
            self.error.emit(f"JSON oluşturma işlemi sırasında genel hata oluştu: {str(e)}")
            app_logger.error(f"JSON oluşturma işlemi sırasında genel hata oluştu: {str(e)}")
        finally:
            self.finished.emit()
            app_logger.info("JSON oluşturma işlemi tamamlandı.")

    def stop(self):
        self.is_running = False
