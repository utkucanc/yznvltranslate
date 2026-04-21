import os
import re
import json
import argparse
import logging
from collections import defaultdict, Counter

# Proje içerisindeki token_counter modülünü dahil et
try:
    from core.workers.token_counter import get_local_token_count_approx
except ImportError:
    def get_local_token_count_approx(text):
        return int(len(text) / 2.5)

# Logging ayarları
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MLExtractor")

# Proje içerisindeki llm_provider modülünü dahil et
try:
    from core.llm_provider import create_provider_from_config
except ImportError as e:
    logger.error("llm_provider.py bulunamadı. Lütfen aracın yznvltranslate-main klasöründe olduğundan emin olun.")
    raise e

EXTRACT_PROMPT_V2 = """Aşağıda sana çevrilmemiş bir web romanının/hikayesinin bağlamını veriyorum.
Lütfen bu metni analiz et ve metinde geçen EN ÖNEMLİ özel karakter isimlerini, yer isimlerini, unvanları ve özel yetenek/teknik isimlerini tespit et.
Bu terimlerin hikaye bağlamına en uygun Türkçe çevirilerini belirle.

LÜTFEN ŞUNU YAP:
1. Yalnızca hikayenin temel taşlarını oluşturan net özel isimleri ve terimleri (isim, yer, teknik vb.) dahil et.
2. Basit kelimeleri listeye EKLEME.
3. Terimleri SADECE 'Kaynak_Dil_Terimi → Türkçe_Çevirisi' formatında listele. Başka hiçbir açıklama yapma, madde imi kullanma.

KAYNAK METİN:
{source_text}

YANIT FORMATI:
source_term → target_translation
"""

class MLTerminologyExtractor:
    """
    MLTerminologyExtractor, verilen proje dizinindeki "dwnld" klasöründen çevrilmemiş metinleri toplayarak, 
    LLM kullanarak önemli terimleri ve çevirilerini çıkartır. 
    Sonuçları "config/terminology.json" dosyasına kaydeder.
    """
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.dwnld_dir = os.path.join(project_path, "dwnld")
        self.config_dir = os.path.join(project_path, "config")
        self.llm_provider = None
        
        try:
            self.llm_provider = create_provider_from_config(project_path)
            logger.info(f"LLM Provider başarıyla yüklendi: {self.llm_provider.ep_name}")
        except Exception as e:
            logger.error(f"LLM Provider başlatılamadı: {e}")

    def _parse_llm_response(self, response: str) -> dict[str, str]:
        extracted = {}
        pattern = re.compile(r'^(.+?)\s*(?:→|->|=)\s*(.+?)$')
        for line in response.strip().split('\n'):
            line = line.strip()
            line = re.sub(r'^[\-\*•]\s*', '', line).strip()
            match = pattern.match(line)
            if match:
                src, tgt = match.group(1).strip(), match.group(2).strip()
                if len(src) >= 1 and len(tgt) >= 1:
                    extracted[src] = tgt
        return extracted

    def _load_ml_max_tokens(self) -> int:
        """AppConfigs/app_settings.json dosyasından ml_max_tokens değerini okur."""
        try:
            settings_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "AppConfigs", "app_settings.json"
            )
            if os.path.exists(settings_path):
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                value = int(settings.get("ml_max_tokens", 200000))
                logger.info(f"ml_max_tokens app_settings.json'dan okundu: {value}")
                return value
        except Exception as e:
            logger.warning(f"app_settings.json okunamadı, varsayılan kullanılıyor: {e}")
        return 200000

    def get_untranslated_files_text(self, target_token_count: int | None = None, margin=0.05,
                                    start_chapter: int | None = None, end_chapter: int | None = None):
        """
        Orijinal dosyaları toplar ve birleştirir.

        Args:
            target_token_count: Maksimum token sayısı (None ise app_settings'den okunur)
            margin: Token limitinin üstüne çıkılabilecek pay oranı (0.05 = %5)
            start_chapter: Dahil edilecek ilk bölüm sırası (1-tabanlı, None ise tümü)
            end_chapter: Dahil edilecek son bölüm sırası (1-tabanlı, None ise tümü)

        Returns:
            Tuple[str, int]: (birleştirilmiş metin, gerçekte işlenen son bölümün 1-tabanlı indeksi)
        """
        if target_token_count is None:
            target_token_count = self._load_ml_max_tokens()

        if not os.path.exists(self.dwnld_dir):
            logger.error(f"Eksik klasör. '{self.dwnld_dir}' bulunamadı.")
            return "", 0

        all_files = sorted([f for f in os.listdir(self.dwnld_dir) if f.endswith(".txt")])

        # Bölüm aralığı filtresi (1-tabanlı indeks)
        if start_chapter is not None or end_chapter is not None:
            s = (start_chapter - 1) if start_chapter and start_chapter >= 1 else 0
            e = end_chapter if end_chapter else len(all_files)
            dwnld_files = all_files[s:e]
            logger.info(f"Bölüm aralığı filtresi uygulandı: {start_chapter}-{end_chapter} "
                        f"→ {len(dwnld_files)} dosya seçildi.")
        else:
            s = 0
            dwnld_files = all_files

        upper_limit = target_token_count * (1 + margin)

        acc_text = ""
        acc_tokens = 0
        actual_end_chapter = s  # Hiç dosya eklenmezse başlangıç ofsetine eşit

        for i, file in enumerate(dwnld_files):
            file_path = os.path.join(self.dwnld_dir, file)
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            current_tokens = get_local_token_count_approx(content)

            # Eğer bu dosyayı eklediğimizde üst limiti aşıyorsa, bu dosyayı eklemeyip kır.
            if acc_tokens + current_tokens > upper_limit:
                logger.info(f"'{file}' ile token limiti ({upper_limit}) %5 sapma dahil aşılıyor. "
                            f"Bu bölüm çıkarıldı ve ekleme durduruluyor.")
                break

            acc_text += content + "\n\n"
            acc_tokens += current_tokens
            actual_end_chapter = s + i + 1  # 1-tabanlı gerçek son bölüm indeksi
            logger.info(f"'{file}' dosyası eklendi. Toplam token sayısı: {acc_tokens}")
            if acc_tokens >= target_token_count:
                logger.info(f"Hedef token sayısına ({target_token_count}) ulaşıldı veya yaklaşıldı. "
                            f"(Güncel: {acc_tokens})")
                break

        logger.info(f"Toplanan metin için tahmini token sayısı: {acc_tokens} | "
                    f"Gerçek son bölüm: {actual_end_chapter}")
        return acc_text, actual_end_chapter


    def run(self, append: bool = False, start_chapter: int | None = None,
            end_chapter: int | None = None, target_token_count: int | None = None):
        """
        Terminoloji çıkarma işlemini başlatır.

        Args:
            append: True ise mevcut terimlere ekler, False ise sıfırdan yazar
            start_chapter: Dahil edilecek ilk bölüm (1-tabanlı)
            end_chapter: Dahil edilecek son bölüm (1-tabanlı)
            target_token_count: Maks token sayısı (None ise app_settings'den)
        """
        if not self.llm_provider:
            logger.error("LLM Provider mevcut olmadığı için işleme devam edilemiyor.")
            return
            
        logger.info("İşlem başlıyor... Dosyalar toplandıyor.")
        
        # Mevcut terminolojiyi yükle (append modunda LLM'e gönderilecek)
        existing_terms = []
        if append:
            terms_file = os.path.join(self.config_dir, "terminology.json")
            if os.path.exists(terms_file):
                try:
                    with open(terms_file, 'r', encoding='utf-8') as f:
                        existing_terms = json.load(f)
                    logger.info(f"Mevcut terminolojiden {len(existing_terms)} terim yüklendi.")
                except Exception as e:
                    logger.warning(f"Mevcut terminoloji okunamadı: {e}")
        
        combined_text, actual_end_chapter = self.get_untranslated_files_text(
            target_token_count=target_token_count,
            margin=0.05,
            start_chapter=start_chapter,
            end_chapter=end_chapter
        )
        if not combined_text.strip():
            logger.warning("Terminoloji çıkarmak için uygun metin bulunamadı.")
            return None
        
        # append modunda mevcut terimleri prompt'a ekleyerek LLM'in önceki terimleri bilmesini sağla
        if append and existing_terms:
            existing_section = "\n\nMEVCUT TERMiNOLOJi (bunlar zaten var, tekrar üretme, sadece YENİ terimleri ekle):\n"
            for t in existing_terms:
                existing_section += f"  {t['source']} \u2192 {t['target']}\n"
            source_text_with_context = combined_text + existing_section
        else:
            source_text_with_context = combined_text

        logger.info("Yapay zekaya terminoloji çıkarma isteği gönderiliyor. Bu işlem model bağlam penceresine göre uzun (1-5 dakika) sürebilir...")
        
        prompt = EXTRACT_PROMPT_V2.format(source_text=source_text_with_context)
        
        try:
            response = self.llm_provider.generate(prompt)
            extracted_dict = self._parse_llm_response(response)
            
            final_terms = []
            for src, tgt in extracted_dict.items():
                final_terms.append({
                    "source": src,
                    "target": tgt,
                    "note": "ml-extracted (long-context)"
                })
                
            logger.info(f"Toplam {len(final_terms)} eşsiz terim çıkarıldı.")
            self._save_results(final_terms, append)
            return actual_end_chapter  # Gerçekte işlenen son bölüm numarası
            
        except Exception as e:
            logger.error(f"Yapay zeka işlemi sırasında hata oluştu: {e}")
            return None


    def _save_results(self, new_terms: list, append: bool):
        os.makedirs(self.config_dir, exist_ok=True)
        terms_file = os.path.join(self.config_dir, "terminology.json")
        
        existing_terms = []
        if append and os.path.exists(terms_file):
            try:
                with open(terms_file, 'r', encoding='utf-8') as f:
                    existing_terms = json.load(f)
            except Exception as e:
                logger.warning(f"Mevcut terminoloji okunamadı: {e}")
                
        if append:
            existing_sources = {t["source"].lower() for t in existing_terms}
            added_terms = []
            skipped_terms = []
            for nt in new_terms:
                if nt["source"].lower() not in existing_sources:
                    existing_terms.append(nt)
                    added_terms.append(nt)
                else:
                    skipped_terms.append(nt)
            final_list = existing_terms
            added_count = len(added_terms)
            logger.info(f"Mevcut listeye {added_count} adet yeni terim eklendi.")
        else:
            final_list = new_terms
            added_terms = new_terms
            skipped_terms = []

        # ── DEV_LOG BAŞLANGIÇ ── (geliştirme aşaması diff raporu — kolayca silinebilir)
        try:
            self._write_dev_diff_log(
                existing_before=existing_terms[:len(existing_terms) - len(added_terms)],
                added_terms=added_terms,
                skipped_terms=skipped_terms,
                append=append,
            )
        except Exception as _dev_err:
            logger.debug(f"[DEV_LOG] Diff raporu yazılamadı: {_dev_err}")
        # ── DEV_LOG BİTİŞ ──
            
        try:
            with open(terms_file, 'w', encoding='utf-8') as f:
                json.dump(final_list, f, indent=2, ensure_ascii=False)
                
            action = "Kayıt mevcut dosyaya EKLENDİ" if append else "YENİ DOSYA YARATILDI"
            logger.info(f"İşlem Tamamlandı: {terms_file} [{action}]")
        except Exception as e:
            logger.error(f"Terminoloji dosyası kaydedilemedi: {e}")

    # ── DEV_LOG YARDIMCI METOT BAŞLANGIÇ ── (geliştirme aşaması — kolayca silinebilir)
    def _write_dev_diff_log(self, existing_before: list, added_terms: list,
                            skipped_terms: list, append: bool):
        """
        Terminoloji işlemi sonrası fark raporu oluşturur.
        Çıktı: proje_dizini/config/terminology_diff.log

        Bu metodun tamamı (ve çağrısı) geliştirme aşaması içindir;
        production'da silinebilir veya devre dışı bırakılabilir.
        """
        import datetime
        log_path = os.path.join(self.config_dir, "terminology_diff.log")
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        lines = []
        lines.append("=" * 70)
        lines.append(f"[DEV DIFF RAPORU]  {now}")
        lines.append(f"Mod: {'EKLE (append)' if append else 'YENİDEN YAZ'}")
        lines.append("=" * 70)

        # ── Mevcut Terimler (işlemden önce) ──
        lines.append(f"\n📚 MEVCUT TERİMLER ÖNCEKİ ({len(existing_before)} adet):")
        if existing_before:
            for i, t in enumerate(existing_before, 1):
                note = f"  [{t.get('note', '')}]" if t.get('note') else ""
                lines.append(f"  {i:>4}. {t['source']}  →  {t['target']}{note}")
        else:
            lines.append("  (boş — ilk çalışma)")

        # ── Yeni Eklenen Terimler ──
        lines.append(f"\n✅ YENİ EKLENEN TERİMLER ({len(added_terms)} adet):")
        if added_terms:
            for i, t in enumerate(added_terms, 1):
                lines.append(f"  {i:>4}. + {t['source']}  →  {t['target']}")
        else:
            lines.append("  (hiç yeni terim eklenmedi)")

        # ── Atlanan Terimler (tekrar) ──
        lines.append(f"\n⏭  ATLANAN TERİMLER — ZATEN MEVCUT ({len(skipped_terms)} adet):")
        if skipped_terms:
            for i, t in enumerate(skipped_terms, 1):
                lines.append(f"  {i:>4}. ~ {t['source']}  →  {t['target']}")
        else:
            lines.append("  (atlanmış terim yok)")

        lines.append("\n" + "=" * 70 + "\n")

        with open(log_path, "a", encoding="utf-8") as f:
            f.write("\n".join(lines))

        # Console'a da kısa özet yaz
        logger.info(
            f"[DEV_LOG] Diff raporu güncellendi → {log_path}\n"
            f"          Mevcut: {len(existing_before)} | "
            f"Yeni eklenen: {len(added_terms)} | "
            f"Atlanan: {len(skipped_terms)}"
        )
        # Yeni eklenenler konsola da bas (hızlı kontrol için)
        if added_terms:
            preview = "\n".join(
                f"          + {t['source']}  →  {t['target']}"
                for t in added_terms[:20]
            )
            if len(added_terms) > 20:
                preview += f"\n          ... ve {len(added_terms) - 20} terim daha"
            logger.info(f"[DEV_LOG] Yeni eklenen terimler:\n{preview}")
    # ── DEV_LOG YARDIMCI METOT BİTİŞ ──


def main():
    parser = argparse.ArgumentParser(description="Uzun Bağlam (Long-Context) ML-Tabanlı Terminoloji Çıkarma")
    parser.add_argument("--project-path", type=str, default=".", help="Projenin ana dizini yolu (varsayılan: ./)")
    parser.add_argument("--append", action="store_true", help="Mevcut terminology.json dosyasının üzerine yazmak yerine terimleri listeye ekle")
    
    args = parser.parse_args()
    extractor = MLTerminologyExtractor(args.project_path)
    extractor.run(append=args.append)

if __name__ == "__main__":
    main()
