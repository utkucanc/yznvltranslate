"""
free_translators.py — Ücretsiz/API tabanlı çeviri servisleri.

Desteklenen sağlayıcılar:
  - google  : GoogleTranslator (proxy desteği, app_settings.json'dan okunur)
  - yandex  : YandexTranslator (API key, app_settings.json'dan okunur)
              Anahtar yoksa MyMemoryTranslator fallback'e düşer.
  - deepl   : DeepLTranslator (API key, app_settings.json'dan okunur)

Yapılandırma (AppConfigs/app_settings.json):
  {
    "deepl_api_key":  "...",
    "yandex_api_key": "...",
    "google_proxy":   {"http": "http://...", "https": "http://..."}
  }

Boş veya eksik alanlar güvenli şekilde atlanır.
"""

import json
import os
import traceback
import logging
from logger import app_logger

logger = logging.getLogger(__name__)

# -- Yapılandırma yardımcısı -------------------------------------------------

_SETTINGS_PATH = os.path.join(os.getcwd(), "AppConfigs", "app_settings.json")


def _load_settings() -> dict:
    """app_settings.json dosyasını yükler; hata olursa boş dict döndürür."""
    try:
        if os.path.exists(_SETTINGS_PATH):
            with open(_SETTINGS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"app_settings.json okunamadı: {e}")
    return {}


def save_setting(key: str, value) -> bool:
    """
    app_settings.json'daki tek bir anahtarı günceller (veya ekler).
    Başarılıysa True, hata oluşursa False döndürür.
    """
    try:
        settings = _load_settings()
        settings[key] = value
        os.makedirs(os.path.dirname(_SETTINGS_PATH), exist_ok=True)
        with open(_SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Ayar kaydedilemedi ({key}): {e}")
        return False


# -- DeepL Sınıfı -------------------------------------------------------------

class DeepLTranslator:
    """
    DeepL API çeviri motoru.

    API anahtarı app_settings.json'daki "deepl_api_key" alanından okunur.
    Aynı zamanda constructor'a doğrudan api_key parametresi verilebilir;
    bu değer app_settings.json'a da kaydedilir.
    """

    def __init__(self, source_lang: str = "ko", target_lang: str = "tr",
                 api_key: str = None):
        self.source_lang = source_lang
        self.target_lang = target_lang

        settings = _load_settings()

        # Parametre verilmişse kaydet, yoksa ayarlardan oku
        if api_key:
            self.api_key = api_key
            save_setting("deepl_api_key", api_key)
        else:
            self.api_key = settings.get("deepl_api_key", "")

        self.translator = None
        self._init_translator()

    def _init_translator(self):
        if not self.api_key:
            logger.warning("DeepL API anahtarı bulunamadı. Çeviri devre dışı.")
            return
        try:
            from deep_translator import DeeplTranslator as _DeeplTranslator
            self.translator = _DeeplTranslator(
                api_key=self.api_key,
                source=self.source_lang,
                target=self.target_lang
            )
        except ImportError:
            logger.error("deep_translator paketi yüklü değil.")
        except Exception as e:
            logger.error(f"DeepL başlatma hatası: {e}")

    def translate(self, text: str) -> str:
        if not text or not text.strip():
            return text
        if self.translator is None:
            raise RuntimeError("DeepL çeviri motoru başlatılamadı (API anahtarı eksik?).")
        try:
            response = self.translator.translate(text)
            if response is None:
                app_logger.error("DeepL çeviri motoru None döndürdü")
                return None
            return response
        except Exception as e:
            logger.error(f"DeepL çeviri hatası: {e}")
            raise


# -- Genel Ücretsiz Motor Sınıfı ----------------------------------------------

class FreeTranslationEngine:
    """
    Birleşik ücretsiz çeviri motoru.

    provider_name:
        "google"  — GoogleTranslator (proxy app_settings.json'dan okunur)
        "yandex"  — YandexTranslator (API key app_settings.json'dan okunur)
                    Anahtar yoksa MyMemoryTranslator fallback
        "deepl"   — DeepLTranslator'a yönlendirilir
    """

    def __init__(self, provider_name: str = "google",
                 source_lang: str = "ko", target_lang: str = "tr",
                 api_key: str = None):
        self.provider_name = provider_name.lower()
        self.source_lang = source_lang
        self.target_lang = target_lang

        # Parametre olarak verilen anahtar ayarları geçersiz kılar
        self._api_key_override = api_key

        self._init_translator()

    # -- Başlatma --

    def _init_translator(self):
        settings = _load_settings()

        if self.provider_name == "google":
            self._init_google(settings)
        elif self.provider_name == "yandex":
            self._init_yandex(settings)
        elif self.provider_name == "deepl":
            self._init_deepl(settings)
        else:
            raise ValueError(f"Desteklenmeyen ücretsiz çeviri motoru: {self.provider_name}")

    def _init_google(self, settings: dict):
        """Google Translate — proxy app_settings.json'dan okunur."""
        try:
            from deep_translator import GoogleTranslator

            proxy_cfg = settings.get("google_proxy", {})
            proxies = {}
            if proxy_cfg.get("http"):
                proxies["http"] = proxy_cfg["http"]
            if proxy_cfg.get("https"):
                proxies["https"] = proxy_cfg["https"]

            if proxies:
                self.translator = GoogleTranslator(
                    source=self.source_lang,
                    target=self.target_lang,
                    proxies=proxies
                )
                logger.debug(f"Google Translate proxy ile başlatıldı: {proxies}")
            else:
                self.translator = GoogleTranslator(
                    source=self.source_lang,
                    target=self.target_lang
                )
                logger.debug("Google Translate proxy olmadan başlatıldı.")
        except ImportError:
            logger.error("deep_translator paketi yüklü değil.")
            raise
        except Exception as e:
            logger.error(f"Google Translate başlatma hatası: {e}")
            raise

    def _init_yandex(self, settings: dict):
        """Yandex Translate — API key varsa YandexTranslator, yoksa MyMemory fallback."""
        api_key = self._api_key_override or settings.get("yandex_api_key", "")

        # Dışarıdan verilen anahtar geldiyse kaydet
        if self._api_key_override:
            save_setting("yandex_api_key", self._api_key_override)

        try:
            if api_key:
                from deep_translator import YandexTranslator
                self.translator = YandexTranslator(
                    api_key=api_key,
                    source=self.source_lang,
                    target=self.target_lang
                )
                logger.debug("Yandex Translate API anahtarı ile başlatıldı.")
            else:
                from deep_translator import MyMemoryTranslator
                # MyMemory dil formatı: "ko-KR" gibi locale kodları gerektirir
                src = _to_mymemory_locale(self.source_lang)
                tgt = _to_mymemory_locale(self.target_lang)
                self.translator = MyMemoryTranslator(source=src, target=tgt)
                logger.debug(
                    "Yandex API anahtarı bulunamadı. "
                    "MyMemory Translator (ücretsiz, sınırlı) kullanılıyor."
                )
        except ImportError:
            logger.error("deep_translator paketi yüklü değil.")
            raise
        except Exception as e:
            logger.error(f"Yandex/MyMemory başlatma hatası: {e}")
            raise

    def _init_deepl(self, settings: dict):
        """DeepL — DeepLTranslator sınıfına yönlendirilir."""
        api_key = self._api_key_override or settings.get("deepl_api_key", "")
        self._deepl_engine = DeepLTranslator(
            source_lang=self.source_lang,
            target_lang=self.target_lang,
            api_key=api_key if api_key else None
        )
        self.translator = None  # translate() _deepl_engine üzerinden çalışır

    # -- Çeviri --

    def translate(self, text: str) -> str:
        if not text or not text.strip():
            return text

        # DeepL özel akış
        if self.provider_name == "deepl":
            return self._deepl_engine.translate(text)

        try:
            response = self.translator.translate(text)
            if response is None:
                app_logger.error(
                    f"{self.provider_name.capitalize()} çeviri motoru None döndürdü"
                )
                return None
            return response
        except Exception as e:
            logger.error(f"{self.provider_name.capitalize()} çeviri hatası: {e}")
            raise


# -- Yardımcı -----------------------------------------------------------------

_MYMEMORY_LOCALES = {
    "ko": "ko-KR",
    "zh": "zh-CN",
    "zh-cn": "zh-CN",
    "zh-tw": "zh-TW",
    "tr": "tr-TR",
    "en": "en-US",
    "ja": "ja-JP",
    "ar": "ar-SA",
    "de": "de-DE",
    "fr": "fr-FR",
    "es": "es-ES",
    "ru": "ru-RU",
}


def _to_mymemory_locale(lang: str) -> str:
    """Kısa dil kodunu MyMemory'nin beklediği locale formatına çevirir."""
    return _MYMEMORY_LOCALES.get(lang.lower(), lang)