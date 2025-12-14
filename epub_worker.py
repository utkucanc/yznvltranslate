import os
import datetime
from PyQt6.QtCore import QObject, pyqtSignal
from ebooklib import epub

class EpubWorker(QObject):
    """
    Seçili metin dosyalarını EPUB formatına dönüştüren işçi sınıfı.
    """
    finished = pyqtSignal(str)  # Başarı mesajı döner
    error = pyqtSignal(str)     # Hata mesajı döner
    progress = pyqtSignal(int, int) # İlerleme durumu

    def __init__(self, file_paths, output_folder, project_name="Kitap"):
        super().__init__()
        self.file_paths = file_paths
        self.output_folder = output_folder
        self.project_name = project_name
        self.is_running = True

    def run(self):
        if not self.file_paths:
            self.error.emit("EPUB oluşturmak için dosya seçilmedi.")
            self.finished.emit("")
            return

        try:
            # Çıktı dosya adı: ProjeAdı_Tarih.epub
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            epub_filename = f"{self.project_name}_{timestamp}.epub"
            epub_path = os.path.join(self.output_folder, epub_filename)

            # Kitap oluştur
            book = epub.EpubBook()
            book.set_identifier(f'id_{timestamp}')
            book.set_title(self.project_name)
            book.set_language('tr')
            book.add_author('NovelAlem Çeviri Aracı')

            chapters = []
            total_files = len(self.file_paths)

            for i, file_path in enumerate(self.file_paths):
                if not self.is_running:
                    self.error.emit("EPUB oluşturma işlemi durduruldu.")
                    break

                file_name = os.path.basename(file_path)
                chapter_title = os.path.splitext(file_name)[0].replace("translated_", "").replace("_", " ")

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # HTML formatlama
                    html_content = f"<h2>{chapter_title}</h2>"
                    paragraphs = content.split('\n')
                    # Boş olmayan paragrafları p etiketiyle sarmala
                    html_content += "".join(f"<p>{p}</p>" for p in paragraphs if p.strip())

                    # Bölümü oluştur
                    chapter = epub.EpubHtml(
                        title=chapter_title,
                        file_name=f'chapter_{i+1}.xhtml',
                        lang='tr'
                    )
                    chapter.content = html_content
                    
                    book.add_item(chapter)
                    chapters.append(chapter)

                except Exception as e:
                    print(f"Uyarı: {file_name} işlenirken hata: {e}")
                
                self.progress.emit(i + 1, total_files)

            if self.is_running:
                # Kitap yapısını tamamla
                book.toc = chapters
                book.spine = ['nav'] + chapters
                book.add_item(epub.EpubNcx())
                book.add_item(epub.EpubNav())

                # Dosyayı kaydet
                epub.write_epub(epub_path, book, {})
                
                self.finished.emit(f"EPUB başarıyla oluşturuldu:\n{epub_filename}")

        except Exception as e:
            self.error.emit(f"EPUB oluşturulurken genel hata: {str(e)}")
        
    def stop(self):
        self.is_running = False