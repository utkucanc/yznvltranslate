"""
Çeviri Hata Kontrol Worker — Çıktı dosyalarındaki çeviri kalitesini,
CJK karakter oranını, metin benzerlik oranını (%80+) ve dil tespitini (langdetect)
kontrolederek hatalı/çevrilmemiş dosyaları tespit eder.
"""

import os
import re
from PyQt6.QtCore import QObject, pyqtSignal
from logger import app_logger
from core.workers.translation_quality_checker import TranslationQualityChecker, _CJK_PATTERN

HIGH_THRESHOLD = 1000  # 1000 karakterden fazla ise yüksek risk
LOW_THRESHOLD = 100    # 100 karakterden fazla ise düşük risk


class TranslationErrorCheckWorker(QObject):
    """
    Çıktı klasöründeki tüm txt dosyalarını kontrol eder.
    CJK karakter oranı, metin benzerliği (>= %80) ve langdetect dil tespiti
    kriterlerine uyan şüpheli/hatalı dosyaları raporlar.
    """
    finished = pyqtSignal(dict)  # Sonuç: {"high": [...], "low": [...], "report_path": str}
    error = pyqtSignal(str)
    progress = pyqtSignal(int, int)

    def __init__(self, folder_path: str, report_folder: str = None, source_lang: str = "en"):
        super().__init__()
        self.folder_path = folder_path
        self.report_folder = report_folder or folder_path
        self.source_lang = source_lang
        self.is_running = True
        
        # dwnld klasörü (orijinal metinler için)
        parent_dir = os.path.dirname(os.path.abspath(folder_path))
        self.dwnld_folder = os.path.join(parent_dir, 'dwnld')

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

            checker = TranslationQualityChecker(
                source_lang=self.source_lang,
                cjk_threshold=0.50,
                similarity_threshold=0.80,
                use_langdetect=True
            )

            high_ratio_files = []  # Hatalı / Yüksek riskli
            low_ratio_files = []   # Şüpheli / Düşük riskli

            for i, filename in enumerate(txt_files):
                if not self.is_running:
                    break

                filepath = os.path.join(self.folder_path, filename)
                
                # Orijinal dosya eşleştirmesi
                orig_filename = filename[11:] if filename.startswith('translated_') else filename
                orig_filepath = os.path.join(self.dwnld_folder, orig_filename)
                
                original_content = ""
                if os.path.exists(orig_filepath):
                    try:
                        with open(orig_filepath, 'r', encoding='utf-8', errors='ignore') as of:
                            original_content = of.read()
                    except Exception as oe:
                        app_logger.warning(f"Orijinal dosya okunamadı ({orig_filename}): {oe}")

                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                    total_chars = len(content)
                    if total_chars == 0:
                        high_ratio_files.append({
                            "filename": filename,
                            "filepath": filepath,
                            "total_chars": 0,
                            "reason": "Boş dosya",
                            "korean_count": 0,
                            "chinese_count": 0,
                            "korean_ratio": 0.0,
                            "chinese_ratio": 0.0,
                            "similarity_ratio": 0.0,
                            "total_asian_count": 0,
                        })
                        self.progress.emit(i + 1, total)
                        continue

                    # Detaylı ölçümler
                    cjk_matches = len(_CJK_PATTERN.findall(content))
                    cjk_ratio = cjk_matches / total_chars if total_chars > 0 else 0.0
                    
                    similarity_ratio = checker.calculate_similarity(original_content, content) if original_content else 0.0
                    
                    # Dil tespiti
                    lang_matched = checker._detected_lang_matches_source(content)

                    reasons = []
                    is_high_risk = False
                    is_low_risk = False

                    # Risk Sebepleri
                    if similarity_ratio >= 0.80:
                        reasons.append(f"Orijinal ile Benzerlik Yüksek (%{similarity_ratio*100:.1f})")
                        is_high_risk = True

                    if cjk_ratio > 0.50:
                        reasons.append(f"Aşırı CJK Karakteri (%{cjk_ratio*100:.1f})")
                        is_high_risk = True
                    elif cjk_matches > LOW_THRESHOLD and cjk_ratio > 0.05:
                        reasons.append(f"CJK Karakter Oranı Yüksek (%{cjk_ratio*100:.1f})")
                        is_high_risk = True
                    elif cjk_matches > LOW_THRESHOLD:
                        reasons.append(f"Düşük CJK Karakteri ({cjk_matches} adet)")
                        is_low_risk = True

                    if lang_matched and not is_high_risk:
                        reasons.append(f"Çeviri Dili Kaynak Dile Eşit ({self.source_lang})")
                        is_high_risk = True

                    file_info = {
                        "filename": filename,
                        "filepath": filepath,
                        "total_chars": total_chars,
                        "reason": ", ".join(reasons) if reasons else "Belirtilmedi",
                        "korean_count": cjk_matches,
                        "chinese_count": cjk_matches,
                        "korean_ratio": cjk_ratio,
                        "chinese_ratio": cjk_ratio,
                        "similarity_ratio": similarity_ratio,
                        "total_asian_count": cjk_matches,
                    }

                    if is_high_risk:
                        high_ratio_files.append(file_info)
                    elif is_low_risk:
                        low_ratio_files.append(file_info)

                except Exception as e:
                    app_logger.error(f"Dosya kontrol hatası ({filename}): {e}")

                self.progress.emit(i + 1, total)

            # Rapor dosyaları oluştur
            report_path = ""
            if self.is_running:
                os.makedirs(self.report_folder, exist_ok=True)

                # Yüksek riskli dosyalar raporu
                high_report = os.path.join(self.report_folder, "hata_kontrol_yuksek.txt")
                with open(high_report, 'w', encoding='utf-8') as f:
                    f.write(f"=== Yüksek Riskli / Hatalı Çevrilmiş Dosyalar ===\n")
                    f.write(f"Toplam: {len(high_ratio_files)} dosya\n\n")
                    for fi in high_ratio_files:
                        f.write(f"Dosya: {fi['filename']}\n")
                        f.write(f"  Sebep: {fi['reason']}\n")
                        f.write(f"  Toplam Karakter: {fi['total_chars']}\n")
                        if fi['similarity_ratio'] > 0:
                            f.write(f"  Orijinal Benzerlik Oranı: %{fi['similarity_ratio']*100:.1f}\n")
                        f.write(f"  Asya/CJK Karakter Sayısı: {fi['total_asian_count']}\n")
                        f.write("-" * 40 + "\n")

                # Düşük riskli dosyalar raporu
                low_report = os.path.join(self.report_folder, "hata_kontrol_dusuk.txt")
                with open(low_report, 'w', encoding='utf-8') as f:
                    f.write(f"=== Düşük Riskli / Şüpheli Dosyalar ===\n")
                    f.write(f"Toplam: {len(low_ratio_files)} dosya\n\n")
                    for fi in low_ratio_files:
                        f.write(f"Dosya: {fi['filename']}\n")
                        f.write(f"  Sebep: {fi['reason']}\n")
                        f.write(f"  Toplam Karakter: {fi['total_chars']}\n")
                        f.write(f"  Asya/CJK Karakter Sayısı: {fi['total_asian_count']}\n")
                        f.write("-" * 40 + "\n")

                report_path = self.report_folder

            self.finished.emit({
                "high": high_ratio_files,
                "low": low_ratio_files,
                "report_path": report_path
            })

        except Exception as e:
            self.error.emit(f"Hata kontrol hatası: {str(e)}")
