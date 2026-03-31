"""
Çeviri Hata Kontrol Worker — Çıktı dosyalarındaki Korece ve Çince karakter
oranını kontrol eder. Ratio > 5% olan dosyaları tespit eder.
"""

import os
import re
from PyQt6.QtCore import QObject, pyqtSignal
from logger import app_logger

# Unicode aralıkları (ch-kontrol.py ve kr-kontrol.py ile uyumlu)
KOREAN_PATTERN = re.compile(r'[\uac00-\ud7a3\u1100-\u11ff\u3130-\u318f]')
CHINESE_PATTERN = re.compile(r'[\u4e00-\u9fff]')

HIGH_THRESHOLD = 1000  # 1000 karakterden fazla ise yüksek risk
LOW_THRESHOLD = 100    # 100 karakterden fazla ise düşük risk


class TranslationErrorCheckWorker(QObject):
    """
    Çıktı klasöründeki tüm txt dosyalarını kontrol eder.
    Korece/Çince karakter oranı > %5 olan dosyaları raporlar.
    """
    finished = pyqtSignal(dict)  # Sonuç: {"high": [...], "low": [...], "report_path": str}
    error = pyqtSignal(str)
    progress = pyqtSignal(int, int)

    def __init__(self, folder_path: str, report_folder: str = None):
        super().__init__()
        self.folder_path = folder_path
        self.report_folder = report_folder or folder_path
        self.is_running = True

    def stop(self):
        self.is_running = False

    def run(self):
        try:
            txt_files = sorted([f for f in os.listdir(self.folder_path)
                                if f.endswith('.txt') and f.startswith('translated_')])
            total = len(txt_files)

            if total == 0:
                self.finished.emit({"high": [], "low": [], "report_path": ""})
                return

            high_ratio_files = []  # ratio > 5%
            low_ratio_files = []   # ratio <= 5%

            for i, filename in enumerate(txt_files):
                if not self.is_running:
                    break

                filepath = os.path.join(self.folder_path, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()

                    total_chars = len(content)
                    if total_chars == 0:
                        self.progress.emit(i + 1, total)
                        continue

                    korean_count = len(KOREAN_PATTERN.findall(content))
                    chinese_count = len(CHINESE_PATTERN.findall(content))
                    total_asian_count = korean_count + chinese_count
                    kratio = korean_count / total_chars
                    cratio = chinese_count / total_chars
                    file_info = {
                        "filename": filename,
                        "filepath": filepath,
                        "total_chars": total_chars,
                        "korean_count": korean_count,
                        "chinese_count": chinese_count,
                        "korean_ratio": kratio,
                        "chinese_ratio": cratio,
                        "total_asian_count": total_asian_count,
                    }

                    if total_asian_count > HIGH_THRESHOLD:
                        if kratio > 0.05 or cratio > 0.05:
                            high_ratio_files.append(file_info)
                        else:
                            low_ratio_files.append(file_info)

                    elif total_asian_count > LOW_THRESHOLD:
                        if kratio < 0.05 and cratio < 0.05:
                            low_ratio_files.append(file_info)
                        elif kratio > 0.05 or cratio > 0.05:
                            high_ratio_files.append(file_info)

                except Exception as e:
                    app_logger.error(f"Dosya kontrol hatası ({filename}): {e}")

                self.progress.emit(i + 1, total)

            # Rapor dosyaları oluştur
            report_path = ""
            if self.is_running:
                os.makedirs(self.report_folder, exist_ok=True)

                # Yüksek oranlılar raporu
                high_report = os.path.join(self.report_folder, "hata_kontrol_yuksek.txt")
                with open(high_report, 'w', encoding='utf-8') as f:
                    f.write(f"=== Yüksek Riskli Dosyalar (>{HIGH_THRESHOLD} karakter ve Korece/Çince karakter oranı > 5%) ===\n")
                    f.write(f"Toplam: {len(high_ratio_files)} dosya\n\n")
                    for fi in high_ratio_files:
                        f.write(f"Dosya: {fi['filename']}\n")
                        f.write(f"  Toplam Karakter: {fi['total_chars']}\n")
                        f.write(f"  Asya Karakter Toplamı: {fi['total_asian_count']}\n")
                        f.write(f"  Korece: {fi['korean_count']} ({fi['korean_ratio']*100:.2f}%)\n")
                        f.write(f"  Çince: {fi['chinese_count']} ({fi['chinese_ratio']*100:.2f}%)\n")
                        f.write("-" * 40 + "\n")

                # Düşük oranlılar raporu
                low_report = os.path.join(self.report_folder, "hata_kontrol_dusuk.txt")
                with open(low_report, 'w', encoding='utf-8') as f:
                    f.write(f"=== Düşük Riskli Dosyalar ({LOW_THRESHOLD}-{HIGH_THRESHOLD} karakter) ===\n")
                    f.write(f"Toplam: {len(low_ratio_files)} dosya\n\n")
                    for fi in low_ratio_files:
                        f.write(f"Dosya: {fi['filename']}\n")
                        f.write(f"  Toplam Karakter: {fi['total_chars']}\n")
                        f.write(f"  Asya Karakter Toplamı: {fi['total_asian_count']}\n")
                        f.write(f"  Korece: {fi['korean_count']} ({fi['korean_ratio']*100:.2f}%)\n")
                        f.write(f"  Çince: {fi['chinese_count']} ({fi['chinese_ratio']*100:.2f}%)\n")
                        f.write("-" * 40 + "\n")

                report_path = self.report_folder

            self.finished.emit({
                "high": high_ratio_files,
                "low": low_ratio_files,
                "report_path": report_path
            })

        except Exception as e:
            self.error.emit(f"Hata kontrol hatası: {str(e)}")
