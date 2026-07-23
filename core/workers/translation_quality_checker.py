"""
translation_quality_checker.py
───────────────────────────────
Çevirinin başarısız olduğunu tespit eden çok katmanlı kontrol modülü.

Kontrol akışı:
  0. Boşluk / kısalık anomalisi   → tüm diller
  1. CJK karakter oranı           → Non-Latin kaynak diller (> %50)
  2. Metin benzerlik oranı        → tüm diller (primer, sıfır bağımlılık, eşik >= %80)
  3. langdetect dil tespiti       → Katman 2 tek başına yeterli değilse devreye girer
"""

import re
from difflib import SequenceMatcher
from logger import app_logger

# Deterministik langdetect — modül yüklendiğinde bir kez ayarlanır
try:
    from langdetect import DetectorFactory
    DetectorFactory.seed = 0
except ImportError:
    pass

# CJK pattern (ch-kontrol.py, kr-kontrol.py ve translation_worker.py ile uyumlu)
_CJK_PATTERN = re.compile(
    r'[\u4e00-\u9fff\uac00-\ud7a3\u1100-\u11ff\u3130-\u318f]'
)


def normalize_text(text: str) -> str:
    """Karşılaştırma için metni normalize eder (küçük harf + boşluk tekleştirme)."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


class TranslationQualityChecker:
    """
    Çeviri kalite kontrolcüsü.

    Kullanım:
        checker = TranslationQualityChecker(source_lang="en")
        if checker.is_translation_failed(original_text, translated_text, "dosya.txt"):
            # Yeniden çevir / Hatalı kabul et
    """

    def __init__(
        self,
        source_lang: str = "en",
        cjk_threshold: float = 0.50,
        similarity_threshold: float = 0.80,
        max_compare_chars: int = 5000,
        min_text_length: int = 50,
        use_langdetect: bool = True,
    ):
        self.source_lang = source_lang.lower() if source_lang else "en"
        self.cjk_threshold = cjk_threshold
        self.similarity_threshold = similarity_threshold
        self.max_compare_chars = max_compare_chars
        self.min_text_length = min_text_length
        self.use_langdetect = use_langdetect
        self._langdetect_available = self._check_langdetect()

    def _check_langdetect(self) -> bool:
        try:
            import langdetect  # noqa: F401
            return True
        except ImportError:
            app_logger.warning(
                "langdetect kütüphanesi bulunamadı. Dil tespiti devre dışı kalacak."
            )
            return False

    def _is_empty_or_too_short(self, original: str, translated: str) -> bool:
        """Metnin boş veya orijinaline kıyasla aşırı kısa olup olmadığını kontrol eder."""
        if not translated or not translated.strip():
            return True
        if original and len(original.strip()) > 50 and len(translated.strip()) < len(original.strip()) * 0.10:
            return True
        return False

    def _has_excessive_cjk(self, text: str) -> bool:
        """CJK/Korece karakter oranının eşiği aşıp aşmadığını kontrol eder."""
        total = len(text)
        if total == 0:
            return False
        count = len(_CJK_PATTERN.findall(text))
        return (count / total) > self.cjk_threshold

    def calculate_similarity(self, original: str, translated: str) -> float:
        """
        Orijinal ve çeviri metinleri arasındaki benzerlik oranını döndürür (0.0 - 1.0).
        """
        if not original or not translated:
            return 0.0

        norm_orig = normalize_text(original[:self.max_compare_chars])
        norm_trans = normalize_text(translated[:self.max_compare_chars])

        if len(norm_orig) < 30 or len(norm_trans) < 30:
            return 0.0

        return SequenceMatcher(None, norm_orig, norm_trans).ratio()

    def _is_too_similar_to_original(self, original: str, translated: str) -> bool:
        """Metin benzerlik oranının eşiği (varsayılan %80) aşıp aşmadığını kontrol eder."""
        ratio = self.calculate_similarity(original, translated)
        if ratio >= self.similarity_threshold:
            app_logger.warning(
                f"Benzerlik kontrolü BAŞARISIZ: oran={ratio:.1%} >= {self.similarity_threshold:.0%} (çevrilmemiş)"
            )
            return True
        return False

    def _detected_lang_matches_source(self, translated: str) -> bool:
        """Çevirilen metnin tespit edilen dili kaynak dille eşleşiyor mu?"""
        if not self.use_langdetect or not self._langdetect_available:
            return False

        stripped = translated.strip()
        if len(stripped) < self.min_text_length:
            return False

        try:
            from langdetect import detect, LangDetectException
            detected = detect(stripped)
            app_logger.debug(f"langdetect tespiti: '{detected}' (kaynak: '{self.source_lang}')")
            if detected == self.source_lang:
                app_logger.warning(
                    f"langdetect BAŞARISIZ: tespit edilen dil '{detected}' kaynak dille aynı."
                )
                return True
        except Exception as e:
            app_logger.debug(f"langdetect tespiti çalıştırılamadı: {e}")

        return False

    def is_translation_failed(
        self,
        original: str,
        translated: str,
        filename: str = "",
    ) -> bool:
        """
        Çevirinin başarısız olup olmadığını çok katmanlı kontrol eder.
        True dönerse çeviri başarısız (çevrilmemiş veya hatalı) kabul edilir.
        """
        prefix = f"[{filename}] " if filename else ""

        # Kontrol 0: Boşluk veya aşırı kısalık
        if self._is_empty_or_too_short(original, translated):
            app_logger.warning(f"{prefix}KaliteKontrol: Çeviri metni boş veya aşırı kısa.")
            return True

        # Kontrol 1: CJK / Asya karakter oranı (> %50)
        if self._has_excessive_cjk(translated):
            app_logger.warning(f"{prefix}KaliteKontrol: Yüksek CJK/Korece karakter oranı.")
            return True

        # Kontrol 2: Orijinal ile benzerlik oranı (>= %80)
        if original and self._is_too_similar_to_original(original, translated):
            app_logger.warning(f"{prefix}KaliteKontrol: Metin benzerlik oranı >= %80 (çevrilmemiş).")
            return True

        # Kontrol 3: langdetect dil tespiti (kaynak dille aynı mı?)
        if self._detected_lang_matches_source(translated):
            app_logger.warning(f"{prefix}KaliteKontrol: Dil tespiti kaynak dile eşit ({self.source_lang}).")
            return True

        return False
