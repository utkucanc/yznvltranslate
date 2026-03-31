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


# ────────────────────── Terim Çıkarma Prompt'u ──────────────────────

EXTRACTION_PROMPT = """Aşağıdaki roman/novel metnini analiz et ve çeviride tutarlılık sağlamak için önemli olan terimleri çıkar.

Terimler şunları içermelidir:
- Özel isimler (karakter isimleri, yer isimleri, dünya isimleri)
- Güç/seviye sistemleri (cultivation stages, rank names vb.)
- Teknik terimler (özel silahlar, büyüler, yetenekler)
- Tekrarlayan kavramlar (Qi, Mana, Dao vb.)

Her terim için kaynak dilde terimi ve Türkçe çevirisini belirle.
Eğer terim çevrilmemeli ise (örn. Qi, Mana) aynı şekilde yaz.

YANITINI TAM OLARAK şu formatta ver (her satırda bir terim):
source_term → target_translation

Örnek:
Nascent Soul → Ruh Embriyosu
Qi → Qi
Spirit Beast → Ruh Canavarı
Heavenly Tribulation → Göksel Bela

SADECE terimleri yaz, başka açıklama ekleme.

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

    # ────────────────────── Yükleme / Kaydetme ──────────────────────

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

    # ────────────────────── Terim CRUD ──────────────────────

    def add_term(self, source: str, target: str, note: str = ""):
        """Terim ekler. Aynı kaynak zaten varsa günceller."""
        for t in self.terms:
            if t["source"].lower() == source.lower():
                t["target"] = target
                t["note"] = note
                self._save()
                return
        self.terms.append({"source": source, "target": target, "note": note})
        self._save()

    def remove_term(self, source: str):
        """Terim siler."""
        self.terms = [t for t in self.terms if t["source"].lower() != source.lower()]
        self._save()

    def get_all_terms(self) -> list[dict]:
        return self.terms

    # ────────────────────── Otomatik Terim Çıkarma ──────────────────────

    def needs_extraction(self) -> bool:
        """Terim listesi boşsa True döner — otomatik çıkarma tetiklenmeli."""
        return len(self.terms) == 0

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
            # Metin çok uzunsa kısalt (token limiti için)
            truncated = sample_text[:8000]

            prompt = EXTRACTION_PROMPT.format(sample_text=truncated)
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
        Beklenen format: her satır 'source → target' veya 'source = target'
        """
        if not raw_response:
            return 0

        count = 0
        # → veya -> veya = ile ayır
        pattern = re.compile(r'^(.+?)\s*(?:→|->|=)\s*(.+?)$')

        for line in raw_response.strip().split('\n'):
            line = line.strip()
            if not line:
                continue

            # Markdown bullet point temizle
            line = re.sub(r'^[\-\*•]\s*', '', line).strip()

            match = pattern.match(line)
            if match:
                source = match.group(1).strip()
                target = match.group(2).strip()

                # Geçerlilik kontrolü
                if source and target and len(source) >= 2 and len(target) >= 1:
                    # Tekrar kontrolü
                    exists = False
                    for t in self.terms:
                        if t["source"].lower() == source.lower():
                            exists = True
                            break

                    if not exists:
                        self.terms.append({
                            "source": source,
                            "target": target,
                            "note": "auto-extracted"
                        })
                        count += 1

        return count

    def get_sample_text_from_project(self, max_files: int = 3) -> str:
        """
        Proje dwnld klasöründen ilk birkaç bölümün metnini toplar.
        Otomatik terim çıkarma için kullanılır.
        """
        dwnld_folder = os.path.join(self.project_path, "dwnld")
        if not os.path.exists(dwnld_folder):
            return ""

        files = sorted([f for f in os.listdir(dwnld_folder) if f.endswith('.txt')])
        if not files:
            return ""

        samples = []
        for f in files[:max_files]:
            try:
                filepath = os.path.join(dwnld_folder, f)
                with open(filepath, 'r', encoding='utf-8') as fh:
                    content = fh.read()[:3000]  # Her dosyadan max 3000 karakter
                    samples.append(content)
            except Exception:
                pass

        return "\n\n---\n\n".join(samples)

    # ────────────────────── Prompt Entegrasyonu ──────────────────────

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

    # ────────────────────── Import / Export ──────────────────────

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
