import time
from logger import app_logger
import unicodedata
import re
class TextUtils:
    @staticmethod
    # ---------------------- Paragraf Bazlı API ----------------------

    def get_paragraph(self, text: str, model_id: str, prompt_hash: str) -> str | None:
        """Tek paragraf için cache arar. Thread-safe."""
        key = self._make_key(text, model_id, prompt_hash)

        with self._lock:
            entry = self._cache.get(key)
            if entry:
                entry["last_access"] = time.time()
                return entry.get("translation")

        return self._fuzzy_search(text, model_id, prompt_hash)

    def set_paragraph(self, text: str, model_id: str, prompt_hash: str, translation: str):
        """Tek paragrafı cache'e yazar. Thread-safe."""
        key = self._make_key(text, model_id, prompt_hash)
        norm_text = self._normalize(text)

        needs_cleanup = False
        with self._lock:
            self._cache[key] = {
                "original_text": text,
                "translation": translation,
                "model_id": model_id,
                "prompt_hash": prompt_hash,
                "created_at": time.time(),
                "last_access": time.time(),
            }
            self._norm_index[key] = norm_text
            if len(self._cache) > self.max_entries:
                needs_cleanup = True

        if needs_cleanup:
            self._cleanup()

        # _save() kilit DIŞINDA, snapshot alarak çalışır
        self._save()
    def get(self, text: str, model_id: str, prompt_hash: str) -> str | None:
        return self.get_paragraph(text, model_id, prompt_hash)

    def set(self, text: str, model_id: str, prompt_hash: str, translation: str):
        self.set_paragraph(text, model_id, prompt_hash, translation)
    @staticmethod
    def split_into_paragraphs(text: str, min_length: int = 20) -> list[str]:
        """Metni paragraflara böler. Çift satır sonu ile ayırır."""
        raw_parts = re.split(r'\n\s*\n', text.strip())
        paragraphs = []
        buffer = ""

        for part in raw_parts:
            part = part.strip()
            if not part:
                continue
            if buffer:
                buffer += "\n\n" + part
            else:
                buffer = part
            if len(buffer) >= min_length:
                paragraphs.append(buffer)
                buffer = ""

        if buffer:
            if paragraphs:
                paragraphs[-1] += "\n\n" + buffer
            else:
                paragraphs.append(buffer)

        return paragraphs if paragraphs else [text]