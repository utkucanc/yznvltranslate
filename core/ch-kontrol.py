import os
import sys

# Çekirdek modülleri bulabilmek için path ayarı
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logger import app_logger
from core.workers.translation_quality_checker import TranslationQualityChecker

def klasoru_tara(klasor_yolu, kaynak_klasor_yolu=None, source_lang="zh"):
    """
    Belirtilen klasördeki txt dosyalarını bulur, kalite ve karakter analizini raporlar.
    """
    if not os.path.exists(klasor_yolu):
        app_logger.error(f"Hata: '{klasor_yolu}' yolu bulunamadı.")
        return []

    app_logger.info(f"--- '{klasor_yolu}' klasörü taranıyor --- Çeviri/Çince Kontrol ---")
    checker = TranslationQualityChecker(source_lang=source_lang, cjk_threshold=0.50, similarity_threshold=0.80)

    silinecek_list = []
    toplam_dosya = 0
    sorunsuz_dosya = 0
    sorunlu_dosya = 0

    for dosya_adi in os.listdir(klasor_yolu):
        if dosya_adi.endswith(".txt"):
            dosya_yolu = os.path.join(klasor_yolu, dosya_adi)
            dosya_tam_yolu = os.path.abspath(dosya_yolu)
            toplam_dosya += 1

            # Orijinal dosya varsa oku
            original_text = ""
            if kaynak_klasor_yolu:
                orig_filename = dosya_adi[11:] if dosya_adi.startswith("translated_") else dosya_adi
                orig_path = os.path.join(kaynak_klasor_yolu, orig_filename)
                if os.path.exists(orig_path):
                    try:
                        with open(orig_path, 'r', encoding='utf-8', errors='ignore') as of:
                            original_text = of.read()
                    except Exception:
                        pass

            try:
                with open(dosya_yolu, 'r', encoding='utf-8', errors='ignore') as f:
                    icerik = f.read()
                    is_failed = checker.is_translation_failed(original_text, icerik, dosya_adi)
                    if is_failed:
                        app_logger.info(f"Dosya: {dosya_adi} -> Hatalı/Çevrilmemiş Tespit Edildi")
                        sorunlu_dosya += 1
                        silinecek_list.append(dosya_tam_yolu)
                    else:
                        sorunsuz_dosya += 1
            except Exception as e:
                app_logger.error(f"Hata: {dosya_adi} okunamadı. Sebebi: {e}")

    if toplam_dosya == 0:
        app_logger.info("Klasörde hiç .txt dosyası bulunamadı.")
    else:
        app_logger.info(f"Sorunlu Dosya Sayısı: {sorunlu_dosya}")
        app_logger.info(f"Sorunsuz Dosya Sayısı: {sorunsuz_dosya}")
        app_logger.info(f"Toplam Dosya Sayısı: {toplam_dosya}")
    return silinecek_list

def dosya_sil(dosya_list):
    if not dosya_list:
        return
    for dosya_yol in dosya_list:
        try:
            os.remove(dosya_yol)
        except Exception as e:
            app_logger.error(f"Silme hatası ({dosya_yol}): {e}")
    app_logger.info("Silme Tamamlandı")

if __name__ == "__main__":
    hedef_klasor = "./trslt"
    kaynak_klasor = "./dwnld" if os.path.exists("./dwnld") else None
    dosya_sil(klasoru_tara(hedef_klasor, kaynak_klasor, source_lang="zh"))