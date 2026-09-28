import os
import re
import json
from PyQt6.QtCore import QObject, pyqtSignal


def _get_split_separator() -> str:
    """app_settings.json'dan split_separator ayarını okur."""
    try:
        settings_path = os.path.join(os.getcwd(), "AppConfigs", "app_settings.json")
        if os.path.exists(settings_path):
            with open(settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            sep = data.get("split_separator", "")
            if sep:
                return sep
    except Exception:
        pass
    return "## Bölüm - {num} ##"


def _separator_to_regex(separator: str) -> str:
    """
    Ayraç şablonunu regex'e dönüştürür.
    {num} ifadesi (\\d+) grubuna çevrilir. Kalan karakterler re.escape ile korunur.
    """
    parts = separator.split("{num}")
    return r"(\d+)".join(re.escape(p) for p in parts)


class SplitWorker(QObject):
    """
    İndirilen toplu bölüm dosyasını başlık kalıbına göre bölerek ayrı dosyalar oluşturur.
    Kullanılan ayraç app_settings.json'daki split_separator ayarından okunur.
    {num} içeren ayraçlarda bölüm numarası ayraçtan okunur;
    içermeyenlerde sıra numarası otomatik atanır.
    """
    finished = pyqtSignal()
    progress = pyqtSignal(int, int)  # (current, total)
    error = pyqtSignal(str)
    file_created = pyqtSignal(str)   # To optionally pass the created file

    def __init__(self, input_file_path, output_folder):
        super().__init__()
        self.input_file_path = input_file_path
        self.output_folder = output_folder
        self.is_running = True

    def run(self):
        try:
            os.makedirs(self.output_folder, exist_ok=True)

            with open(self.input_file_path, "r", encoding="utf-8") as f:
                icerik = f.read()

            separator_template = _get_split_separator()
            has_num = "{num}" in separator_template

            if has_num:
                # {num} varsa: capture group ile böl → ["", "1", "metin", "2", "metin", ...]
                regex_pattern = _separator_to_regex(separator_template)
                bolumler = re.split(regex_pattern, icerik)

                if len(bolumler) <= 1:
                    self.error.emit(
                        f"Dosyada uygun '{separator_template}' başlığı bulunamadı."
                    )
                    self.finished.emit()
                    return

                # re.split ile gelen liste: ["", "1", "bölüm metni", "2", "bölüm metni", ...]
                # Bu yüzden 1'den başlatıp 2'şer adım ilerleyeceğiz
                valid_chunks = list(range(1, len(bolumler), 2))
                total_chapters = len(valid_chunks)
                processed = 0

                for i in valid_chunks:
                    if not self.is_running:
                        break

                    bolum_numara = bolumler[i].strip()
                    bolum_metin = bolumler[i + 1].strip()

                    # Çıktı dosyası formatı
                    dosya_adi = f"bolum_{bolum_numara.zfill(4)}.txt"
                    dosya_yolu = os.path.join(self.output_folder, dosya_adi)

                    with open(dosya_yolu, "w", encoding="utf-8") as f:
                        f.write(bolum_metin)

                    processed += 1
                    self.progress.emit(processed, total_chapters)
                    self.file_created.emit(dosya_adi)

            else:
                # {num} yoksa: sabit ayraç, capture group yok → ["metin", "metin", ...]
                regex_pattern = re.escape(separator_template)
                bolumler = re.split(regex_pattern, icerik)

                # Baştaki boş / ayraçsız metin parçasını atla
                bolumler = [b for b in bolumler if b.strip()]

                if not bolumler:
                    self.error.emit(
                        f"Dosyada uygun '{separator_template}' başlığı bulunamadı."
                    )
                    self.finished.emit()
                    return

                total_chapters = len(bolumler)
                processed = 0

                for idx, bolum_metin in enumerate(bolumler, start=1):
                    if not self.is_running:
                        break

                    bolum_metin = bolum_metin.strip()

                    # {num} olmadığı için sıra numarasını kendimiz atıyoruz
                    dosya_adi = f"bolum_{str(idx).zfill(4)}.txt"
                    dosya_yolu = os.path.join(self.output_folder, dosya_adi)

                    with open(dosya_yolu, "w", encoding="utf-8") as f:
                        f.write(bolum_metin)

                    processed += 1
                    self.progress.emit(processed, total_chapters)
                    self.file_created.emit(dosya_adi)

            self.finished.emit()

        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit()

    def stop(self):
        self.is_running = False
