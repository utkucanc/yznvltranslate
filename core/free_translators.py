import traceback
from logger import app_logger
import logging
from deep_translator import GoogleTranslator, YandexTranslator, MyMemoryTranslator

logger = logging.getLogger(__name__)

class FreeTranslationEngine:
    def __init__(self, provider_name="google", source_lang="ko", target_lang="tr", api_key=None):
        self.provider_name = provider_name.lower()
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.api_key = "dict.1.1.20260811T133439Z.18055c531f84a740.37f982ef0ffc5e149f22a2395de7bdf256add999"
        self._init_translator()

    def _init_translator(self):
        if self.provider_name == "google":
            self.proxies = {
                "https": "http://1.231.81.166:3128",
                "http": "http://1.231.81.166:3128"
            }
            self.translator = GoogleTranslator(source=self.source_lang, target=self.target_lang, proxies=self.proxies)
        elif self.provider_name == "yandex":
            self.translator = MyMemoryTranslator(source="ko-KR", target="tr-TR")
            # Yandex ücretsiz kullanım için API Key gerektirebilir veya deep-translator scraping modunu kullanır
            #if self.api_key:
            #    self.translator = YandexTranslator(api_key=self.api_key, source=self.source_lang, target=self.target_lang)
            #else:
            #    self.translator = YandexTranslator(source=self.source_lang, target=self.target_lang)
        #else:
        #    raise ValueError(f"Desteklenmeyen ücretsiz çeviri motoru: {self.provider_name}")

    def translate(self, text: str) -> str:
        if not text or not text.strip():
            return text
        try:
            response = self.translator.translate(text)
            if response is None:
                app_logger.error(
                    f"{self.provider_name.capitalize()} çeviri motoru None döndürdü"
                )
                return None
            return response
        except Exception as e:
            logger.error(
                f"{self.provider_name.capitalize()} çeviri hatası: {e}"
            )
            raise e