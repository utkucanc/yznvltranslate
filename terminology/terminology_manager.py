"""
Terminology Manager — Proje bazlı terim/terminoloji sözlüğü yönetimi.

Özellikler:
  - Otomatik terim çıkarma: LLM ile ilk bölümlerden terim çıkarır
  - Çeviri promptuna otomatik olarak terim kuralları ekler
  - Proje config/terminology.json dosyasında saklanır
  - Case-insensitive terim eşleştirme
  - Toplu import/export desteği
"""

import os
import json
import re
from logger import app_logger


# ---------------------- Terim Çıkarma Prompt'u ----------------------

EXTRACTION_PROMPT = """Aşağıdaki roman/novel metnini analiz et ve çeviride tutarlılık sağlamak için terimleri çıkar.

ÖNEMLİ: Çıkardığın her terim, daha sonra metnin HER YERİNDE bağlamdan bağımsız şekilde otomatik olarak değiştirilecek. Bu yüzden sadece gerçekten güvenilir, tekrarlayan ve bu hikayeye özgü terimleri çıkar.

Terimler şunları içermelidir:
- Özel isimler (karakter isimleri, yer isimleri, dünya isimleri, teşkilat/klan isimleri)
- Güç/seviye sistemleri (cultivation stages, rank names vb.)
- Teknik terimler (özel silahlar, büyüler, yetenekler, eşyalar)
- Tekrarlayan ve dünyaya özgü kavramlar (Qi, Mana, Dao vb.)

AŞAĞIDAKİLERİ ÇIKARMA:
- Metinde sadece bir kez geçen, tekrarlanmayan ifadeler
- Genel sıfatlar, zarflar veya betimleyici ifadeler
- Sayılar, tarihler, ölçü birimleri
- Günlük dilde de sık kullanılan sıradan kelimeler (örn. "Brother", "Master", "Friend") — SADECE bir ismin yerine geçen özel bir hitap/unvan olarak tutarlı şekilde kullanıldığından eminsen dahil et; emin değilsen "belirsiz: evet" olarak işaretle

Her terim için:
1. Kaynak metindeki TAM YAZIM ŞEKLİYLE (büyük/küçük harf dahil) terimi ver — bu, terimin metinde birebir aranıp değiştirilmesi için kullanılacak
2. Türkçe çevirisini ver (çevrilmemesi gerekiyorsa örn. Qi, Mana, aynı şekilde yaz)
3. Terimin belirsiz/riskli olup olmadığını belirt (metnin başka yerlerinde farklı, sıradan bir anlamda da geçebilir mi?)

YANITINI TAM OLARAK şu formatta ver (her satırda bir terim, alanlar " :: " ile ayrılmış):
kaynak_terim → türkçe_çeviri :: belirsiz(evet/hayır)

Örnek:
Nascent Soul → Ruh Embriyosu :: hayır
Qi → Qi :: hayır
Spirit Beast → Ruh Canavarı :: hayır
Heavenly Tribulation → Göksel Bela :: hayır
Brother → Kardeş :: evet

SADECE terimleri yaz, başka açıklama, başlık veya numaralandırma ekleme.

---

İşte analiz edilecek metin:

{sample_text}
"""


class TerminologyManager:
    """Proje bazlı terminoloji yöneticisi — otomatik terim çıkarma destekli."""

    def __init__(self, project_path: str):
        self.project_path = project_path
        self.terms_file = os.path.join(project_path, "config", "terminology.json")
        self.terms: list[dict] = self._load()
        self._pattern_cache = None
        self._pattern_cache_key = None

    # ---------------------- Yükleme / Kaydetme ----------------------

    def _load(self) -> list[dict]:
        if os.path.exists(self.terms_file):
            try:
                with open(self.terms_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data if isinstance(data, list) else []
            except Exception as e:
                app_logger.warning(f"Terminology dosyası yüklenemedi: {e}")
        return []

    def _save(self):
        os.makedirs(os.path.dirname(self.terms_file), exist_ok=True)
        try:
            with open(self.terms_file, 'w', encoding='utf-8') as f:
                json.dump(self.terms, f, indent=2, ensure_ascii=False)
        except Exception as e:
            app_logger.error(f"Terminology dosyası kaydedilemedi: {e}")

    # ---------------------- Terim CRUD ----------------------

    def add_term(self, source: str, target: str, note: str = "",ambiguous: bool = False):
        """Terim ekler. Aynı kaynak zaten varsa günceller."""
        for t in self.terms:
            if t["source"].lower() == source.lower():
                t["target"] = target
                t["note"] = note
                t["ambiguous"] = ambiguous
                self._save()
                self._invalidate_pattern_cache()
                return
        self.terms.append({"source": source, "target": target, "note": note, "ambiguous": ambiguous})
        self._save()
        self._invalidate_pattern_cache()

    def remove_term(self, source: str):
        """Terim siler."""
        self.terms = [t for t in self.terms if t["source"].lower() != source.lower()]
        self._save()

    def get_all_terms(self) -> list[dict]:
        return self.terms

    # ---------------------- Otomatik Terim Çıkarma ----------------------

    def needs_extraction(self, min_terms: int = 5) -> bool:
        """Terim listesi boşsa veya çok az terim varsa True döner — otomatik çıkarma tetiklenmeli."""
        return len(self.terms) < min_terms

    def auto_extract_terms(self, sample_text: str, provider) -> int:
        """
        LLM ile metinden otomatik terim çıkarır.

        Args:
            sample_text: Analiz edilecek örnek metin (ilk birkaç bölümden)
            provider: LLMProvider instance'ı

        Returns:
            Eklenen terim sayısı
        """
        if not sample_text or not provider:
            app_logger.warning("Otomatik terim çıkarma: metin veya provider eksik.")
            return 0

        try:
            prompt = EXTRACTION_PROMPT.format(sample_text=sample_text)
            app_logger.info("Otomatik terim çıkarma başlatıldı...")

            raw_response = provider.generate(prompt)
            count = self._parse_extracted_terms(raw_response)

            if count > 0:
                self._save()
                app_logger.info(f"Otomatik terim çıkarma tamamlandı: {count} terim eklendi.")
            else:
                app_logger.warning("Otomatik terim çıkarma: LLM yanıtından terim parse edilemedi.")

            return count

        except Exception as e:
            app_logger.error(f"Otomatik terim çıkarma hatası: {e}")
            return 0

    def _parse_extracted_terms(self, raw_response: str) -> int:
        """
        LLM yanıtını parse eder.
        Beklenen format: 'source → target' veya 'source → target :: belirsiz(evet/hayır)'
        (':: ' yoksa eski format gibi davranır, geriye dönük uyumludur)
        """
        if not raw_response:
            return 0

        count = 0
        pattern = re.compile(r'^(.+?)\s*(?:→|->|=)\s*(.+?)$')

        for line in raw_response.strip().split('\n'):
            line = line.strip()
            if not line:
                continue

            line = re.sub(r'^[\-\*•]\s*', '', line).strip()

            match = pattern.match(line)
            if not match:
                continue

            source = match.group(1).strip()
            rest = match.group(2).strip()

            # YENİ: ":: belirsiz(evet/hayır)" kuyruğunu ayır
            ambiguous = False
            if "::" in rest:
                target_part, flag_part = rest.split("::", 1)
                target = target_part.strip()
                ambiguous = "evet" in flag_part.strip().lower()
            else:
                target = rest

            if source and target and len(source) >= 2 and len(target) >= 1:
                exists = any(t["source"].lower() == source.lower() for t in self.terms)
                if not exists:
                    self.terms.append({
                        "source": source,
                        "target": target,
                        "note": "auto-extracted",
                        "ambiguous": ambiguous,   # YENİ ALAN
                    })
                    count += 1

        if count:
            self._invalidate_pattern_cache()   # aşağıda ekleyeceğiz
        return count

    def get_sample_text_from_project(self, max_files: int = 5, token_limit: int = 10000) -> str:
        """
        Proje dwnld klasöründen ilk birkaç bölümün metnini toplar.
        Token limiti aşılırsa dosya eklemeyi durdurur.
        Otomatik terim çıkarma için kullanılır.
        """
        try:
            from core.workers.token_counter import get_local_token_count_approx
        except ImportError:
            def get_local_token_count_approx(text):
                return int(len(text) / 2.5)

        dwnld_folder = os.path.join(self.project_path, "dwnld")
        if not os.path.exists(dwnld_folder):
            return ""

        files = sorted([f for f in os.listdir(dwnld_folder) if f.endswith('.txt')])
        if not files:
            return ""

        samples = []
        total_tokens = 0
        for f in files[:max_files]:
            try:
                filepath = os.path.join(dwnld_folder, f)
                with open(filepath, 'r', encoding='utf-8') as fh:
                    content = fh.read()
                file_tokens = get_local_token_count_approx(content)
                if total_tokens + file_tokens > token_limit and samples:
                    app_logger.info(f"Token limiti ({token_limit}) aşılacak, '{f}' eklenmedi.")
                    break
                samples.append(content)
                total_tokens += file_tokens
                app_logger.info(f"'{f}' örnekleme için eklendi. Toplam token: {total_tokens}")
            except Exception:
                pass

        return "\n\n---\n\n".join(samples)
    def _get_compiled_pattern(self, sources: tuple, source_lang: str):
        cache_key = (sources, source_lang)
        if self._pattern_cache_key == cache_key:
            return self._pattern_cache

        sorted_sources = sorted(sources, key=len, reverse=True)  # uzun terim önce
        escaped = [re.escape(s) for s in sorted_sources]

        if source_lang in ("zh", "ja", "ko"):
            # CJK kaynaklarda \b güvenilir çalışmaz (boşluksuz yazım)
            body = "|".join(escaped)
        else:
            body = "|".join(rf"\b{e}\b" for e in escaped)

        pattern = re.compile(body, re.IGNORECASE)
        self._pattern_cache_key = cache_key
        self._pattern_cache = pattern
        return pattern

    def _invalidate_pattern_cache(self):
        self._pattern_cache_key = None
        self._pattern_cache = None

    def build_injected_source(self, text: str, source_lang: str = "en",
                            include_ambiguous: bool = False) -> str:
        """
        Terminoloji sözlüğündeki terimleri kaynak metne enjekte eder.
        build_prompt_section()'ın yerini alır — artık AI'a ayrı bir
        terminoloji bloğu göndermek yerine terimler kaynak metnin
        içine gömülür.
        """
        if not self.terms:
            return text

        active_terms = [
            t for t in self.terms
            if include_ambiguous or not t.get("ambiguous", False)
        ]
        if not active_terms:
            return text

        sources = tuple(t["source"] for t in active_terms)
        pattern = self._get_compiled_pattern(sources, source_lang)
        lookup = {t["source"].lower(): t["target"] for t in active_terms}

        def _replace(m):
            return lookup.get(m.group(0).lower(), m.group(0))

        return pattern.sub(_replace, text)

    def get_pending_review_terms(self) -> list[dict]:
        """Terminology Manager UI'da 'gözden geçirilmeli' listesi için."""
        return [t for t in self.terms if t.get("ambiguous", False)]

    def approve_term(self, source: str):
        """UI'dan bir terim onaylandığında ambiguous=False yapar."""
        for t in self.terms:
            if t["source"].lower() == source.lower():
                t["ambiguous"] = False
                self._save()
                self._invalidate_pattern_cache()
                return
    # ---------------------- Prompt Entegrasyonu ----------------------

    def build_prompt_section(self) -> str:
        """Çeviri promptuna eklenecek terminology bölümünü oluşturur."""
        if not self.terms:
            return ""

        lines = ["[TERMİNOLOJİ KURALLARI - Aşağıdaki terimleri çeviride birebir kullanın:]"]
        for t in self.terms:
            line = f"  • {t['source']} → {t['target']}"
            if t.get("note") and t["note"] != "auto-extracted":
                line += f" ({t['note']})"
            lines.append(line)
        lines.append("[TERMİNOLOJİ SONU]")
        return "\n".join(lines)

    # ---------------------- Import / Export ----------------------

    def import_from_text(self, text: str, delimiter: str = "="):
        """Düz metinden toplu import (her satır: source=target)."""
        count = 0
        for line in text.strip().split("\n"):
            line = line.strip()
            if delimiter in line:
                parts = line.split(delimiter, 1)
                if len(parts) == 2:
                    self.add_term(parts[0].strip(), parts[1].strip())
                    count += 1
        return count

    def export_to_text(self, delimiter: str = "=") -> str:
        """Terimleri düz metin olarak dışa aktarır."""
        lines = []
        for t in self.terms:
            lines.append(f"{t['source']}{delimiter}{t['target']}")
        return "\n".join(lines)

    def clear(self):
        """Tüm terimleri siler."""
        self.terms = []
        self._save()
