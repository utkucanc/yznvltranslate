"""
free_translators.py — Ücretsiz / API tabanlı çeviri servisleri ve Proxy yönetimi.

Desteklenen sağlayıcılar:
  - google : GoogleTranslator (deep_translator, proxy desteği)
  - yandex : YandexTranslator / Yandex Dictionary API / MyMemory fallback
  - deepl  : DeepLTranslator (Doğrudan REST API, Free & Pro desteği, rotasyon)

Yapılandırma (AppConfigs/app_settings.json):
  {
    "deepl_keys": ["c01ea513-42bf-4285-ba2f-7f201f666f7f:fx"],
    "deepl_use_rotation": true,
    "deepl_api_key": "c01ea513-42bf-4285-ba2f-7f201f666f7f:fx",
    "yandex_keys": ["dict.1.1.20260811T133439Z..."],
    "yandex_use_rotation": true,
    "yandex_api_key": "dict.1.1.20260811T133439Z...",
    "proxies": [
      {
        "id": "proxy_1",
        "type": "socks4",
        "host": "185.147.69.48",
        "port": 1080,
        "username": "",
        "password": "",
        "active": true
      }
    ],
    "google_proxy": {"http": "...", "https": "..."}
  }
"""

import json
import os
import threading
import requests
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


def load_free_translators_config() -> dict:
    """Ücretsiz çeviriciler ve proxy ayarlarını yükler ve standart yapı döndürür."""
    settings = _load_settings()
    
    deepl_keys = settings.get("deepl_keys", [])
    if not deepl_keys and settings.get("deepl_api_key"):
        deepl_keys = [settings.get("deepl_api_key").strip()]

    yandex_keys = settings.get("yandex_keys", [])
    if not yandex_keys and settings.get("yandex_api_key"):
        yandex_keys = [settings.get("yandex_api_key").strip()]

    proxies = settings.get("proxies", [])

    return {
        "deepl_keys": [k for k in deepl_keys if k and k.strip()],
        "deepl_use_rotation": settings.get("deepl_use_rotation", True),
        "yandex_keys": [k for k in yandex_keys if k and k.strip()],
        "yandex_use_rotation": settings.get("yandex_use_rotation", True),
        "proxies": proxies,
        "google_proxy": settings.get("google_proxy", {})
    }


def save_free_translators_config(data: dict) -> bool:
    """Ücretsiz çeviriciler ve proxy ayarlarını app_settings.json'a kaydeder."""
    try:
        settings = _load_settings()
        if "deepl_keys" in data:
            settings["deepl_keys"] = data["deepl_keys"]
            settings["deepl_api_key"] = data["deepl_keys"][0] if data["deepl_keys"] else ""
        if "deepl_use_rotation" in data:
            settings["deepl_use_rotation"] = bool(data["deepl_use_rotation"])

        if "yandex_keys" in data:
            settings["yandex_keys"] = data["yandex_keys"]
            settings["yandex_api_key"] = data["yandex_keys"][0] if data["yandex_keys"] else ""
        if "yandex_use_rotation" in data:
            settings["yandex_use_rotation"] = bool(data["yandex_use_rotation"])

        if "proxies" in data:
            settings["proxies"] = data["proxies"]

        if "google_proxy" in data:
            settings["google_proxy"] = data["google_proxy"]

        os.makedirs(os.path.dirname(_SETTINGS_PATH), exist_ok=True)
        with open(_SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Free translators ayarları kaydedilemedi: {e}")
        return False


# -- Proxy Yardımcıları -------------------------------------------------------

def format_proxy_url(proxy_dict: dict) -> str:
    """Proxy sözlüğünden requests/urllib uyumlu URL oluşturur."""
    p_type = (proxy_dict.get("type") or "http").lower()
    host = (proxy_dict.get("host") or "").strip()
    port = str(proxy_dict.get("port") or "").strip()
    username = (proxy_dict.get("username") or "").strip()
    password = (proxy_dict.get("password") or "").strip()

    if not host or not port:
        return ""

    if username:
        auth = f"{username}:{password}@" if password else f"{username}@"
        return f"{p_type}://{auth}{host}:{port}"
    return f"{p_type}://{host}:{port}"


def test_proxy_connection(proxy_dict: dict, timeout: int = 6) -> tuple[bool, str]:
    """
    Verilen proxy üzerinden gerçek bağlantı testi yapar.
    (success, message) döndürür.
    """
    proxy_url = format_proxy_url(proxy_dict)
    if not proxy_url:
        return False, "Proxy adresi veya portu eksik."

    proxies = {"http": proxy_url, "https": proxy_url}
    try:
        resp = requests.get("https://httpbin.org/ip", proxies=proxies, timeout=timeout)
        if resp.status_code == 200:
            origin = resp.json().get("origin", "Bilinmeyen IP")
            return True, f"Bağlantı başarılı. Dış IP: {origin}"
        return False, f"Proxy sunucusu HTTP {resp.status_code} kodu döndürdü."
    except requests.exceptions.Timeout:
        return False, f"Zaman aşımı: {timeout} saniye içinde proxy sunucusuna ulaşılamadı."
    except requests.exceptions.ConnectionError as ce:
        return False, f"Bağlantı reddedildi veya sunucuya ulaşılamıyor ({type(ce).__name__})."
    except Exception as e:
        return False, f"Proxy testi başarısız: {str(e)}"


# -- Key Pool Yöneticisi (Round-Robin) ----------------------------------------

class FreeKeyPool:
    """API anahtar havuzunu yönetir (Round-Robin ve tekil kullanım destekler)."""

    def __init__(self, provider: str, keys: list[str] = None, use_rotation: bool = True):
        self.provider = provider
        self.use_rotation = use_rotation
        self.keys = [k.strip() for k in (keys or []) if k and k.strip()]
        self._index = 0
        self._lock = threading.Lock()

    def get_key(self) -> str | None:
        """Havuzdan sıradaki anahtarı döndürür."""
        with self._lock:
            if not self.keys:
                return None
            if self.use_rotation:
                key = self.keys[self._index % len(self.keys)]
                self._index += 1
                return key
            return self.keys[0]

    def has_keys(self) -> bool:
        return len(self.keys) > 0


# -- DeepL Sınıfı -------------------------------------------------------------

class DeepLTranslator:
    """
    DeepL REST API çeviri motoru.
    
    Özellikler:
      - 'Authorization: DeepL-Auth-Key <key>' başlığıyla doğrudan HTTP POST kullanır.
      - ':fx' ile biten anahtarlar için otomatik api-free.deepl.com,
        diğer anahtarlar için api.deepl.com adresini seçer.
      - FreeKeyPool ile birden çok anahtar arasında Round-Robin rotasyon destekler.
    """

    def __init__(self, source_lang: str = "ko", target_lang: str = "tr",
                 api_key: str = None, key_pool: FreeKeyPool = None):
        self.source_lang = source_lang
        self.target_lang = target_lang

        if key_pool:
            self.key_pool = key_pool
        elif api_key:
            self.key_pool = FreeKeyPool("deepl", [api_key], use_rotation=False)
        else:
            cfg = load_free_translators_config()
            self.key_pool = FreeKeyPool("deepl", cfg["deepl_keys"], use_rotation=cfg["deepl_use_rotation"])

    def translate(self, text: str) -> str:
        if not text or not text.strip():
            return text

        if not self.key_pool.has_keys():
            raise RuntimeError("DeepL API anahtarı bulunamadı. Lütfen ayarlardan bir anahtar ekleyin.")

        # Key pool'daki anahtarları sırayla dene (hata durumunda rotasyon)
        keys_to_try = len(self.key_pool.keys) if self.key_pool.use_rotation else 1
        last_error = None

        for attempt in range(keys_to_try):
            key = self.key_pool.get_key()
            if not key:
                continue

            try:
                result = self._call_deepl(text, key)
                if result is not None:
                    return result
            except Exception as e:
                last_error = e
                logger.warning(f"DeepL anahtarı ile çeviri başarısız ({key[:8]}...): {e}")

        if last_error:
            raise last_error
        raise RuntimeError("DeepL çeviri motoru yanıt vermedi.")

    def _call_deepl(self, text: str, api_key: str) -> str:
        base_url = "https://api-free.deepl.com/v2/translate" if api_key.endswith(":fx") else "https://api.deepl.com/v2/translate"
        headers = {
            "Authorization": f"DeepL-Auth-Key {api_key}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        # Hedef dil formatı (büyük harf)
        tgt = self.target_lang.upper()
        if tgt == "EN":
            tgt = "EN-US"
        elif tgt == "PT":
            tgt = "PT-PT"

        data = {
            "text": text,
            "target_lang": tgt
        }

        src = (self.source_lang or "").strip().upper()
        if src and src not in ("AUTO", ""):
            data["source_lang"] = src

        resp = requests.post(base_url, headers=headers, data=data, timeout=15)

        if resp.status_code == 200:
            res_json = resp.json()
            translations = res_json.get("translations", [])
            if translations:
                return translations[0].get("text", "")
            raise RuntimeError("DeepL boş çeviri listesi döndürdü.")
        elif resp.status_code == 403:
            raise RuntimeError(f"DeepL Yetkilendirme Hatası (403): API anahtarı geçersiz ({api_key[:8]}...).")
        elif resp.status_code == 456:
            raise RuntimeError("DeepL Kota Hatası (456): Çeviri kotanız doldu.")
        elif resp.status_code == 429:
            raise RuntimeError("DeepL Rate Limit (429): Çok fazla istek gönderildi.")
        else:
            raise RuntimeError(f"DeepL API Hatası ({resp.status_code}): {resp.text}")

    @staticmethod
    def test_connection(api_key: str) -> tuple[bool, str]:
        """DeepL API anahtarını gerçek bir çağrı ile test eder."""
        if not api_key or not api_key.strip():
            return False, "API anahtarı boş bırakılamaz."

        key = api_key.strip()
        base_url = "https://api-free.deepl.com/v2/translate" if key.endswith(":fx") else "https://api.deepl.com/v2/translate"
        headers = {
            "Authorization": f"DeepL-Auth-Key {key}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "text": "Hello world",
            "target_lang": "TR"
        }

        try:
            resp = requests.post(base_url, headers=headers, data=data, timeout=8)
            if resp.status_code == 200:
                res_json = resp.json()
                trans = res_json.get("translations", [])
                if trans:
                    return True, f"Bağlantı başarılı: {trans[0].get('text', '')}"
                return True, "Bağlantı başarılı (yanıt alındı)."
            elif resp.status_code == 403:
                return False, "API anahtarı geçersiz veya yetkisiz (HTTP 403 Forbidden)."
            elif resp.status_code == 456:
                return False, "API kotası tükenmiş (HTTP 456 Quota Exceeded)."
            else:
                return False, f"DeepL Hatası ({resp.status_code}): {resp.text}"
        except requests.exceptions.Timeout:
            return False, "Zaman aşımı: DeepL sunucusuna ulaşılamadı."
        except Exception as e:
            return False, f"Bağlantı hatası: {str(e)}"


# -- Yandex Sınıfı ------------------------------------------------------------

class YandexTranslator:
    """
    Yandex çeviri motoru.
    
    Özellikler:
      - 'dict.1.1...' anahtarları için Yandex Dictionary API'sini kullanır.
      - 'trnsl.1.1...' veya diğer anahtarlar için Yandex Translate / deep_translator dener.
      - Anahtar yoksa veya API yanıt vermezse MyMemoryTranslator fallback'e başvurur.
      - FreeKeyPool ile anahtar rotasyonu destekler.
    """

    def __init__(self, source_lang: str = "ko", target_lang: str = "tr",
                 api_key: str = None, key_pool: FreeKeyPool = None):
        self.source_lang = source_lang
        self.target_lang = target_lang

        if key_pool:
            self.key_pool = key_pool
        elif api_key:
            self.key_pool = FreeKeyPool("yandex", [api_key], use_rotation=False)
        else:
            cfg = load_free_translators_config()
            self.key_pool = FreeKeyPool("yandex", cfg["yandex_keys"], use_rotation=cfg["yandex_use_rotation"])

    def translate(self, text: str) -> str:
        if not text or not text.strip():
            return text

        # 1. Anahtar varsa Yandex Dictionary / Translate dene
        if self.key_pool.has_keys():
            keys_to_try = len(self.key_pool.keys) if self.key_pool.use_rotation else 1
            for _ in range(keys_to_try):
                key = self.key_pool.get_key()
                if not key:
                    continue
                try:
                    if key.startswith("dict."):
                        result = self._translate_with_dict(text, key)
                        if result:
                            return result
                    else:
                        result = self._translate_with_yandex_api(text, key)
                        if result:
                            return result
                except Exception as e:
                    logger.warning(f"Yandex anahtarı ile çeviri başarısız ({key[:8]}...): {e}")

        # 2. Fallback: MyMemory Translator
        logger.debug("Yandex anahtarı yok veya sonuç vermedi, MyMemory fallback devrede.")
        return self._translate_with_mymemory(text)

    def _translate_with_dict(self, text: str, api_key: str) -> str | None:
        """Yandex Dictionary API lookup."""
        src = "en" if self.source_lang.lower() in ("auto", "") else self.source_lang.lower()
        tgt = self.target_lang.lower()
        lang_pair = f"{src}-{tgt}"

        url = "https://dictionary.yandex.net/api/v1/dicservice.json/lookup"
        params = {
            "key": api_key,
            "text": text.strip(),
            "lang": lang_pair
        }

        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            defs = data.get("def", [])
            if defs and defs[0].get("tr"):
                return defs[0]["tr"][0].get("text", text)
        return None

    def _translate_with_yandex_api(self, text: str, api_key: str) -> str | None:
        """deep_translator YandexTranslator."""
        try:
            from deep_translator import YandexTranslator as _YT
            yt = _YT(api_key=api_key, source=self.source_lang, target=self.target_lang)
            return yt.translate(text)
        except Exception:
            return None

    def _translate_with_mymemory(self, text: str) -> str:
        from deep_translator import MyMemoryTranslator
        src = _to_mymemory_locale(self.source_lang)
        tgt = _to_mymemory_locale(self.target_lang)
        translator = MyMemoryTranslator(source=src, target=tgt)
        res = translator.translate(text)
        if res is None:
            raise RuntimeError("MyMemory Translator None döndürdü.")
        return res

    @staticmethod
    def test_connection(api_key: str) -> tuple[bool, str]:
        """Yandex API anahtarını gerçek bir çağrı ile test eder."""
        if not api_key or not api_key.strip():
            return False, "API anahtarı boş bırakılamaz."

        key = api_key.strip()
        if key.startswith("dict."):
            url = "https://dictionary.yandex.net/api/v1/dicservice.json/lookup"
            try:
                resp = requests.get(url, params={"key": key, "text": "hello", "lang": "en-tr"}, timeout=8)
                if resp.status_code == 200:
                    data = resp.json()
                    defs = data.get("def", [])
                    tr_text = defs[0]["tr"][0].get("text", "") if (defs and defs[0].get("tr")) else "OK"
                    return True, f"Bağlantı başarılı (Sözlük Çevirisi: {tr_text})"
                elif resp.status_code in (401, 403):
                    return False, "Yandex Sözlük API anahtarı geçersiz veya yetkisiz (401/403)."
                else:
                    return False, f"Yandex Hatası ({resp.status_code}): {resp.text}"
            except Exception as e:
                return False, f"Bağlantı hatası: {str(e)}"
        else:
            # Standart Yandex Translate testi
            try:
                from deep_translator import YandexTranslator as _YT
                yt = _YT(api_key=key, source="en", target="tr")
                res = yt.translate("hello")
                if res:
                    return True, f"Bağlantı başarılı: {res}"
                return False, "Yandex boş yanıt döndürdü."
            except Exception as e:
                return False, f"Yandex API Hatası: {str(e)}"


# -- Genel Ücretsiz Motor Sınıfı (Polymorphic) --------------------------------

class FreeTranslationEngine:
    """
    Birleşik ücretsiz çeviri motoru.

    provider_name:
        "google"  — GoogleTranslator (proxy app_settings.json'dan okunur)
        "yandex"  — YandexTranslator (Key pool & rotasyon destekli)
        "deepl"   — DeepLTranslator (Key pool & rotasyon destekli)
    """

    def __init__(self, provider_name: str = "google",
                 source_lang: str = "ko", target_lang: str = "tr",
                 api_key: str = None):
        self.provider_name = provider_name.lower()
        self.source_lang = source_lang
        self.target_lang = target_lang
        self._api_key_override = api_key

        self._init_translator()

    def _init_translator(self):
        cfg = load_free_translators_config()

        if self.provider_name == "google":
            self._init_google(cfg)
        elif self.provider_name == "yandex":
            self._init_yandex(cfg)
        elif self.provider_name == "deepl":
            self._init_deepl(cfg)
        else:
            raise ValueError(f"Desteklenmeyen ücretsiz çeviri motoru: {self.provider_name}")

    def _init_google(self, cfg: dict):
        """Google Translate — proxy yapılandırmasıyla başlatır."""
        try:
            from deep_translator import GoogleTranslator

            proxy_cfg = cfg.get("google_proxy", {})
            proxies = {}

            # Tekil http/https kontrolü veya aktif proxy listesinden
            if proxy_cfg.get("http"):
                proxies["http"] = proxy_cfg["http"]
            if proxy_cfg.get("https"):
                proxies["https"] = proxy_cfg["https"]

            # Eğer proxies listesinde aktif olan varsa ve google_proxy boşsa
            if not proxies and cfg.get("proxies"):
                for p in cfg["proxies"]:
                    if p.get("active"):
                        p_url = format_proxy_url(p)
                        if p_url:
                            proxies = {"http": p_url, "https": p_url}
                        break

            if proxies:
                self._engine = GoogleTranslator(
                    source=self.source_lang,
                    target=self.target_lang,
                    proxies=proxies
                )
                logger.debug(f"Google Translate proxy ile başlatıldı: {proxies}")
            else:
                self._engine = GoogleTranslator(
                    source=self.source_lang,
                    target=self.target_lang
                )
                logger.debug("Google Translate proxy olmadan başlatıldı.")
        except Exception as e:
            logger.error(f"Google Translate başlatma hatası: {e}")
            raise

    def _init_yandex(self, cfg: dict):
        """Yandex motorunu key pool ile başlatır."""
        key_pool = None
        if self._api_key_override:
            key_pool = FreeKeyPool("yandex", [self._api_key_override], use_rotation=False)
        else:
            key_pool = FreeKeyPool("yandex", cfg["yandex_keys"], use_rotation=cfg["yandex_use_rotation"])

        self._engine = YandexTranslator(
            source_lang=self.source_lang,
            target_lang=self.target_lang,
            key_pool=key_pool
        )

    def _init_deepl(self, cfg: dict):
        """DeepL motorunu key pool ile başlatır."""
        key_pool = None
        if self._api_key_override:
            key_pool = FreeKeyPool("deepl", [self._api_key_override], use_rotation=False)
        else:
            key_pool = FreeKeyPool("deepl", cfg["deepl_keys"], use_rotation=cfg["deepl_use_rotation"])

        self._engine = DeepLTranslator(
            source_lang=self.source_lang,
            target_lang=self.target_lang,
            key_pool=key_pool
        )

    def translate(self, text: str) -> str:
        """Polymorphic translate çağrısı."""
        if not text or not text.strip():
            return text
        try:
            result = self._engine.translate(text)
            if result is None:
                app_logger.error(f"{self.provider_name.capitalize()} çeviri motoru None döndürdü")
                return None
            return result
        except Exception as e:
            logger.error(f"{self.provider_name.capitalize()} çeviri hatası: {e}")
            raise


# -- Yardımcı Locale Eşlemeleri ----------------------------------------------

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