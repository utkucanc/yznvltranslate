"""
Translation Cache — Paragraf bazlı çeviri önbelleği.

Özellikler:
  - Paragraf bazlı cache: her paragraf ayrı ayrı cache'lenir
  - Exact hash match: SHA-1(normalized_text + model_id + prompt_hash)
  - Fuzzy matching: Karakter n-gram Jaccard similarity ile %85+ benzerlikte cache hit
  - LRU temizlik: max_entries aşıldığında en az kullanılan girişler silinir
  - JSON dosya bazlı kalıcı depolama
"""

import os
import json
import hashlib
import time
import unicodedata
import re
from logger import app_logger


class TranslationCache:
    """Proje bazlı paragraf seviyesinde çeviri önbelleği."""

    # Fuzzy matching eşik değeri (0.0 - 1.0)
    FUZZY_THRESHOLD = 0.85
    # N-gram boyutu
    NGRAM_SIZE = 3
    # Fuzzy arama sırasında taranacak maksimum giriş sayısı (performans limiti)
    MAX_FUZZY_SCAN = 5000

    def __init__(self, project_path: str, max_entries: int = 100000):
        self.cache_folder = os.path.join(project_path, "config", "cache")
        os.makedirs(self.cache_folder, exist_ok=True)
        self.cache_file = os.path.join(self.cache_folder, "translation_cache.json")
        self.max_entries = max_entries
        self._cache = self._load()

        # In-memory normalize text index: {key: normalized_text}
        # Fuzzy arama için kullanılır
        self._norm_index: dict[str, str] = {}
        self._build_norm_index()

    # ────────────────────── Yükleme / Kaydetme ──────────────────────

    def _load(self) -> dict:
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                app_logger.warning(f"Cache dosyası yüklenemedi: {e}")
        return {}

    def _save(self):
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self._cache, f, ensure_ascii=False)
        except Exception as e:
            app_logger.error(f"Cache dosyası kaydedilemedi: {e}")

    def _build_norm_index(self):
        """Mevcut cache girişlerinden normalize text index'i oluşturur."""
        self._norm_index.clear()
        for key, entry in self._cache.items():
            orig = entry.get("original_text", "")
            if orig:
                self._norm_index[key] = self._normalize(orig)

    # ────────────────────── Hash / Normalize ──────────────────────

    @staticmethod
    def _normalize(text: str) -> str:
        """Metni normalize eder: küçük harf, fazla boşluk temizleme, Unicode NFC."""
        text = unicodedata.normalize("NFC", text)
        text = text.lower().strip()
        text = re.sub(r'\s+', ' ', text)
        return text

    @staticmethod
    def _make_key(text: str, model_id: str, prompt_hash: str) -> str:
        """Kesin eşleşme için SHA-1 hash üretir."""
        norm = TranslationCache._normalize(text)
        raw = f"{norm}|{model_id}|{prompt_hash}"
        return hashlib.sha1(raw.encode('utf-8')).hexdigest()

    @staticmethod
    def hash_prompt(prompt: str) -> str:
        return hashlib.sha1(prompt.encode('utf-8')).hexdigest()[:12]

    # ────────────────────── N-gram Similarity ──────────────────────

    @staticmethod
    def _char_ngrams(text: str, n: int = 3) -> set:
        """Metinden karakter n-gramları çıkarır."""
        if len(text) < n:
            return {text} if text else set()
        return {text[i:i + n] for i in range(len(text) - n + 1)}

    @classmethod
    def _ngram_similarity(cls, a: str, b: str) -> float:
        """İki normalize metin arasında Jaccard similarity (0.0 - 1.0)."""
        if a == b:
            return 1.0
        if not a or not b:
            return 0.0

        # Uzunluk farkı çok büyükse hesaplamaya gerek yok
        len_ratio = min(len(a), len(b)) / max(len(a), len(b))
        if len_ratio < 0.5:
            return 0.0

        ngrams_a = cls._char_ngrams(a, cls.NGRAM_SIZE)
        ngrams_b = cls._char_ngrams(b, cls.NGRAM_SIZE)

        intersection = len(ngrams_a & ngrams_b)
        union = len(ngrams_a | ngrams_b)

        if union == 0:
            return 0.0
        return intersection / union

    # ────────────────────── Paragraf Bazlı API ──────────────────────

    def get_paragraph(self, text: str, model_id: str, prompt_hash: str) -> str | None:
        """
        Tek paragraf için cache arar.
        Önce exact hash match, sonra fuzzy matching dener.
        """
        # 1. Exact match
        key = self._make_key(text, model_id, prompt_hash)
        entry = self._cache.get(key)
        if entry:
            entry["last_access"] = time.time()
            return entry.get("translation")

        # 2. Fuzzy match
        return self._fuzzy_search(text, model_id, prompt_hash)

    def set_paragraph(self, text: str, model_id: str, prompt_hash: str, translation: str):
        """Tek paragrafı cache'e yazar."""
        key = self._make_key(text, model_id, prompt_hash)
        norm_text = self._normalize(text)
        self._cache[key] = {
            "original_text": text,
            "translation": translation,
            "model_id": model_id,
            "prompt_hash": prompt_hash,
            "created_at": time.time(),
            "last_access": time.time(),
        }
        # Normalize index'i güncelle
        self._norm_index[key] = norm_text

        # LRU temizlik
        if len(self._cache) > self.max_entries:
            self._cleanup()

        self._save()

    def _fuzzy_search(self, text: str, model_id: str, prompt_hash: str) -> str | None:
        """
        Cache'deki girişleri tarayarak fuzzy eşleşme arar.
        model_id ve prompt_hash uyumlu girişlerle sınırlıdır.
        """
        norm_text = self._normalize(text)
        if not norm_text or len(norm_text) < 10:
            return None  # Çok kısa metinlerde fuzzy aramama

        best_score = 0.0
        best_key = None
        scan_count = 0

        for key, cached_norm in self._norm_index.items():
            # Performans limiti
            scan_count += 1
            if scan_count > self.MAX_FUZZY_SCAN:
                break

            entry = self._cache.get(key)
            if not entry:
                continue

            # Model ve prompt uyumu kontrolü
            if entry.get("model_id") != model_id:
                continue
            if entry.get("prompt_hash") != prompt_hash:
                continue

            score = self._ngram_similarity(norm_text, cached_norm)
            if score > best_score:
                best_score = score
                best_key = key

        if best_score >= self.FUZZY_THRESHOLD and best_key:
            entry = self._cache[best_key]
            entry["last_access"] = time.time()
            app_logger.info(
                f"Fuzzy cache hit (benzerlik: {best_score:.2%}): "
                f"'{text[:50]}...' → cached"
            )
            return entry.get("translation")

        return None

    # ────────────────────── Eski API (geriye uyumluluk) ──────────────────────

    def get(self, text: str, model_id: str, prompt_hash: str) -> str | None:
        """
        Dosya bazlı önbellek sorgusu (geriye uyumluluk).
        Tüm dosya içeriğini tek parça olarak arar.
        """
        return self.get_paragraph(text, model_id, prompt_hash)

    def set(self, text: str, model_id: str, prompt_hash: str, translation: str):
        """Dosya bazlı önbellek kaydı (geriye uyumluluk)."""
        self.set_paragraph(text, model_id, prompt_hash, translation)

    # ────────────────────── Paragraf Bölme Yardımcısı ──────────────────────

    @staticmethod
    def split_into_paragraphs(text: str, min_length: int = 20) -> list[str]:
        """
        Metni paragraflara böler. Çift satır sonu ile ayırır.
        Çok kısa paragrafları bir sonrakiyle birleştirir.
        """
        # Çift newline ile böl
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

        # Kalan buffer varsa ekle
        if buffer:
            if paragraphs:
                paragraphs[-1] += "\n\n" + buffer
            else:
                paragraphs.append(buffer)

        return paragraphs if paragraphs else [text]

    # ────────────────────── Temizlik / İstatistik ──────────────────────

    def remove(self, text: str, model_id: str, prompt_hash: str):
        """Belirli bir cache girişini siler."""
        key = self._make_key(text, model_id, prompt_hash)
        if key in self._cache:
            del self._cache[key]
            self._norm_index.pop(key, None)
            self._save()
            app_logger.info(f"Hatalı cache girişi silindi: {key[:12]}...")

    def _cleanup(self):
        """En eski girişleri siler (LRU)."""
        if len(self._cache) <= self.max_entries:
            return

        entries = sorted(self._cache.items(), key=lambda x: x[1].get("last_access", 0))
        remove_count = len(self._cache) - self.max_entries
        for i in range(remove_count):
            key = entries[i][0]
            del self._cache[key]
            self._norm_index.pop(key, None)

        app_logger.info(f"Cache temizliği: {remove_count} giriş silindi.")

    def clear(self):
        """Tüm cache'i temizler."""
        self._cache = {}
        self._norm_index.clear()
        self._save()

    def stats(self) -> dict:
        """Cache istatistikleri."""
        return {
            "entries": len(self._cache),
            "max_entries": self.max_entries,
            "file_size": os.path.getsize(self.cache_file) if os.path.exists(self.cache_file) else 0,
        }
