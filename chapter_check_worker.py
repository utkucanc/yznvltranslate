import os
from PyQt6.QtCore import QObject, pyqtSignal

class ChapterCheckWorker(QObject):
    """
    Seçili dosyaların ilk 3 satırında 'Bölüm' kelimesini arayan
    ve sonuçları raporlayan işçi sınıfı.
    Eğer 'Bölüm' kelimesi bulunamazsa, dosyanın başına 'Başlıksız Bölüm' ekler.
    """
    finished = pyqtSignal(str) # İşlem bitince mesaj döner
    error = pyqtSignal(str)
    progress = pyqtSignal(int, int)

    def __init__(self, project_path, files_to_check):
        super().__init__()
        self.project_path = project_path
        self.files_to_check = files_to_check # List of (filename, full_path)
        self.is_running = True

    def run(self):
        if not self.files_to_check:
            self.finished.emit("Kontrol edilecek dosya bulunamadı.")
            return

        # Hedef klasörleri oluştur: cmplt/bkontrol
        bkontrol_path = os.path.join(self.project_path, 'cmplt', 'bkontrol')
        os.makedirs(bkontrol_path, exist_ok=True)

        var_list = [] # (filename, line_content)
        yok_list = [] # filename

        try:
            total_files = len(self.files_to_check)
            
            for i, (filename, file_path) in enumerate(self.files_to_check):
                if not self.is_running:
                    break
                
                found_bolum = False
                found_line_content = ""

                try:
                    if os.path.exists(file_path):
                        # Önce sadece kontrol için ilk 3 satırı oku
                        lines_to_check = []
                        with open(file_path, 'r', encoding='utf-8') as f:
                            for _ in range(3):
                                line = f.readline()
                                if not line: break
                                lines_to_check.append(line)
                        
                        for line in lines_to_check:
                            if "Bölüm" in line:
                                found_bolum = True
                                found_line_content = line.strip()
                                break
                        
                        if found_bolum:
                            var_list.append((filename, found_line_content))
                        else:
                            yok_list.append(filename)
                            # "Bölüm" bulunamadı, dosyanın tamamını oku ve başına ekle
                            with open(file_path, 'r', encoding='utf-8') as f:
                                original_content = f.read()
                            
                            new_content = "Başlıksız Bölüm\n" + original_content
                            
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(new_content)

                    else:
                        pass

                except Exception as e:
                    print(f"Hata ({filename}): {e}")
                
                self.progress.emit(i + 1, total_files)

            # Rapor dosyalarını oluştur
            if self.is_running:
                # Yok.txt
                with open(os.path.join(bkontrol_path, 'Yok.txt'), 'w', encoding='utf-8') as f_yok:
                    for fname in yok_list:
                        f_yok.write(f"{fname}\n")

                # Var.txt
                with open(os.path.join(bkontrol_path, 'Var.txt'), 'w', encoding='utf-8') as f_var:
                    for fname, content in var_list:
                        f_var.write(f"{fname}\n{content}\n{'-'*20}\n")

                result_message = (f"İşlem tamamlandı.\n"
                                  f"Klasör: cmplt/bkontrol\n"
                                  f"'Bölüm' Olanlar: {len(var_list)}\n"
                                  f"'Bölüm' Olmayanlar: {len(yok_list)} (Otomatik Eklendi)")
                self.finished.emit(result_message)

        except Exception as e:
            self.error.emit(f"Başlık kontrolü sırasında hata: {str(e)}")

    def stop(self):
        self.is_running = False