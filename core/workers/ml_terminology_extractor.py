from core.localization import tr_log
import os
import re
import json
import argparse
import logging
import threading
import time
from core.workers.rate_limiter import get_limiter
from collections import defaultdict, Counter
from core.localization import tr
_terminology_save_lock = threading.Lock()
try:
    from core.workers.token_counter import get_local_token_count_approx
except ImportError:

    def get_local_token_count_approx(text):
        return int(len(text) / 2.5)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('MLExtractor')
try:
    from core.llm_provider import create_provider_from_config
except ImportError as e:
    logger.error(tr_log('core.workers.ml_terminology_extractor', 27, 'llm_provider.py bulunamadı. Lütfen aracın yznvltranslate-main klasöründe olduğundan emin olun.'))
    raise e

def _get_extract_prompt() -> str:
    """
    app_settings.json'daki ml_extractor_prompt_override boş değilse onu döndürür,
    boşsa locale'den gelen varsayılan promptu kullanır.
    """
    try:
        import json as _json
        _settings_file = os.path.join(os.getcwd(), 'AppConfigs', 'app_settings.json')
        if os.path.exists(_settings_file):
            with open(_settings_file, 'r', encoding='utf-8') as _f:
                _data = _json.load(_f)
            override = _data.get('ml_extractor_prompt_override', '').strip()
            if override:
                return override
    except Exception:
        pass
    return tr('ml_terminology_extractor.promt_part1', '') + '{source_text}' + tr('ml_terminology_extractor.promt_part2', '')
EXTRACT_PROMPT_V2 = tr('ml_terminology_extractor.promt_part1', '') + '{source_text}' + tr('ml_terminology_extractor.promt_part2', '')
from core.path_resolver import get_subfolder_path

class MLTerminologyExtractor:
    """
    MLTerminologyExtractor, verilen proje dizinindeki indirilen metinler klasöründen çevrilmemiş metinleri toplayarak, 
    LLM kullanarak önemli terimleri ve çevirilerini çıkartır. 
    Sonuçları "config/terminology.json" dosyasına kaydeder.
    """

    def __init__(self, project_path: str):
        self.project_path = project_path
        self.dwnld_dir = get_subfolder_path(project_path, 'download')
        self.config_dir = get_subfolder_path(project_path, 'config')
        self.llm_provider = None
        try:
            self.llm_provider = create_provider_from_config(project_path)
            logger.info(tr_log('core.workers.ml_terminology_extractor', 68, f'LLM Provider başarıyla yüklendi: {self.llm_provider.ep_name}'))
        except Exception as e:
            logger.error(tr_log('core.workers.ml_terminology_extractor', 70, f'LLM Provider başlatılamadı: {e}'))
    
    def _generate_with_retry(self, prompt: str, max_retries: int = 3):
        tokens = get_local_token_count_approx(prompt)
        limiter = get_limiter()
        for attempt in range(max_retries + 1):
            limiter.acquire(tokens)
            try:
                return self.llm_provider.generate(prompt)
            except Exception as e:
                msg = str(e).lower()
                is_rate = any(k in msg for k in ('429', 'rate', 'quota', 'resource_exhausted', 'tpm', 'rpm'))
                if not is_rate:
                    raise
                if attempt == max_retries:
                    logger.error(tr_log('ml_terminology_extractor.retry_error',"Max deneyeme ulaşıltı. İşlem Durduruluyor."))
                    raise
                wait = min(20 * (2 ** attempt), 120)  # 20, 40, 80, 120...
                logger.warning(f'Rate limit hatası, {wait} sn beklenip tekrar denenecek ({attempt + 1}/{max_retries})')
                time.sleep(wait)
                
    def _parse_llm_response(self, response: str) -> dict[str, str]:
        extracted = {}
        pattern = re.compile('^(.+?)\\s*(?:→|->|=)\\s*(.+?)$')
        for line in response.strip().split('\n'):
            line = line.strip()
            line = re.sub('^[\\-\\*•]\\s*', '', line).strip()
            match = pattern.match(line)
            if match:
                (src, tgt) = (match.group(1).strip(), match.group(2).strip())
                if len(src) >= 1 and len(tgt) >= 1:
                    extracted[src] = tgt
        return extracted

    def _load_ml_max_tokens(self) -> int:
        """AppConfigs/app_settings.json dosyasından ml_max_tokens değerini okur."""
        try:
            settings_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'AppConfigs', 'app_settings.json')
            if os.path.exists(settings_path):
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                value = int(settings.get('ml_max_tokens', 200000))
                logger.info(tr_log('core.workers.ml_terminology_extractor', 96, f"ml_max_tokens app_settings.json'dan okundu: {value}"))
                return value
        except Exception as e:
            logger.warning(tr_log('core.workers.ml_terminology_extractor', 99, f'app_settings.json okunamadı, varsayılan kullanılıyor: {e}'))
        return 200000

    def get_untranslated_files_text(self, target_token_count: int | None=None, margin=0.05, start_chapter: int | None=None, end_chapter: int | None=None):
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
            logger.error(tr_log('core.workers.ml_terminology_extractor', 120, f"Eksik klasör. '{self.dwnld_dir}' bulunamadı."))
            return ('', 0)
        all_files = sorted([f for f in os.listdir(self.dwnld_dir) if f.endswith('.txt')])
        if start_chapter is not None or end_chapter is not None:
            s = start_chapter - 1 if start_chapter and start_chapter >= 1 else 0
            e = end_chapter if end_chapter else len(all_files)
            dwnld_files = all_files[s:e]
            logger.info(tr_log('core.workers.ml_terminology_extractor', 130, f'Bölüm aralığı filtresi uygulandı: {start_chapter}-{end_chapter} → {len(dwnld_files)} dosya seçildi.'))
        else:
            s = 0
            dwnld_files = all_files
        upper_limit = target_token_count * (1 + margin)
        acc_text = ''
        acc_tokens = 0
        actual_end_chapter = s
        for (i, file) in enumerate(dwnld_files):
            file_path = os.path.join(self.dwnld_dir, file)
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            current_tokens = get_local_token_count_approx(content)
            if acc_tokens + current_tokens > upper_limit:
                logger.info(tr_log('core.workers.ml_terminology_extractor', 151, f"'{file}' ile token limiti ({upper_limit}) %5 sapma dahil aşılıyor. Bu bölüm çıkarıldı ve ekleme durduruluyor."))
                break
            acc_text += content + '\n\n'
            acc_tokens += current_tokens
            actual_end_chapter = s + i + 1
            logger.info(tr_log('core.workers.ml_terminology_extractor', 158, f"'{file}' dosyası eklendi. Toplam token sayısı: {acc_tokens}"))
            if acc_tokens >= target_token_count:
                logger.info(tr_log('core.workers.ml_terminology_extractor', 160, f'Hedef token sayısına ({target_token_count}) ulaşıldı veya yaklaşıldı. (Güncel: {acc_tokens})'))
                break
        logger.info(tr_log('core.workers.ml_terminology_extractor', 164, f'Toplanan metin için tahmini token sayısı: {acc_tokens} | Gerçek son bölüm: {actual_end_chapter}'))
        return (acc_text, actual_end_chapter)

    def run(self, append: bool=False, start_chapter: int | None=None, end_chapter: int | None=None, target_token_count: int | None=None):
        """
        Terminoloji çıkarma işlemini başlatır.

        Args:
            append: True ise mevcut terimlere ekler, False ise sıfırdan yazar
            start_chapter: Dahil edilecek ilk bölüm (1-tabanlı)
            end_chapter: Dahil edilecek son bölüm (1-tabanlı)
            target_token_count: Maks token sayısı (None ise app_settings'den)
        """
        if not self.llm_provider:
            logger.error(tr_log('core.workers.ml_terminology_extractor', 181, 'LLM Provider mevcut olmadığı için işleme devam edilemiyor.'))
            return
        logger.info(tr_log('core.workers.ml_terminology_extractor', 184, 'İşlem başlıyor... Dosyalar toplandıyor.'))
        existing_terms = []
        if append:
            terms_file = os.path.join(self.config_dir, 'terminology.json')
            if os.path.exists(terms_file):
                try:
                    with open(terms_file, 'r', encoding='utf-8') as f:
                        existing_terms = json.load(f)
                    logger.info(tr_log('core.workers.ml_terminology_extractor', 194, f'Mevcut terminolojiden {len(existing_terms)} terim yüklendi.'))
                except Exception as e:
                    logger.warning(tr_log('core.workers.ml_terminology_extractor', 196, f'Mevcut terminoloji okunamadı: {e}'))
        (combined_text, actual_end_chapter) = self.get_untranslated_files_text(target_token_count=target_token_count, margin=0.05, start_chapter=start_chapter, end_chapter=end_chapter)
        if not combined_text.strip():
            logger.warning(tr_log('core.workers.ml_terminology_extractor', 205, 'Terminoloji çıkarmak için uygun metin bulunamadı.'))
            return None
        if append and existing_terms:
            existing_section = '\n\nMEVCUT TERMiNOLOJi (bunlar zaten var, tekrar üretme, sadece YENİ terimleri ekle):\n'
            for t in existing_terms:
                existing_section += f"  {t['source']} → {t['target']}\n"
            source_text_with_context = combined_text + existing_section
        else:
            source_text_with_context = combined_text
        logger.info(tr_log('core.workers.ml_terminology_extractor', 217, 'Yapay zekaya terminoloji çıkarma isteği gönderiliyor. Bu işlem model bağlam penceresine göre uzun (1-5 dakika) sürebilir...'))
        prompt = _get_extract_prompt().format(source_text=source_text_with_context)
        try:
            response = self._generate_with_retry(prompt)
            extracted_dict = self._parse_llm_response(response)
            final_terms = []
            for (src, tgt) in extracted_dict.items():
                final_terms.append({'source': src, 'target': tgt, 'note': 'ml-extracted (long-context)'})
            logger.info(tr_log('core.workers.ml_terminology_extractor', 233, f'Toplam {len(final_terms)} eşsiz terim çıkarıldı.'))
            self._save_results(final_terms, append)
            return actual_end_chapter
        except Exception as e:
            logger.error(tr_log('core.workers.ml_terminology_extractor', 238, f'Yapay zeka işlemi sırasında hata oluştu: {e}'))
            return None

    def _save_results(self, new_terms: list, append: bool):
        with _terminology_save_lock:
            os.makedirs(self.config_dir, exist_ok=True)
            terms_file = os.path.join(self.config_dir, 'terminology.json')
            existing_terms = []
            if append and os.path.exists(terms_file):
                try:
                    with open(terms_file, 'r', encoding='utf-8') as f:
                        existing_terms = json.load(f)
                except Exception as e:
                    logger.warning(tr_log('core.workers.ml_terminology_extractor', 253, f'Mevcut terminoloji okunamadı: {e}'))
            if append:
                existing_sources = {t['source'].lower() for t in existing_terms}
                added_terms = []
                skipped_terms = []
                for nt in new_terms:
                    if nt['source'].lower() not in existing_sources:
                        existing_terms.append(nt)
                        added_terms.append(nt)
                    else:
                        skipped_terms.append(nt)
                final_list = existing_terms
                added_count = len(added_terms)
                logger.info(tr_log('core.workers.ml_terminology_extractor', 267, f'Mevcut listeye {added_count} adet yeni terim eklendi.'))
            else:
                final_list = new_terms
                added_terms = new_terms
                skipped_terms = []
            try:
                with open(terms_file, 'w', encoding='utf-8') as f:
                    json.dump(final_list, f, indent=2, ensure_ascii=False)
                action = 'Kayıt mevcut dosyaya EKLENDİ' if append else 'YENİ DOSYA YARATILDI'
                logger.info(tr_log('core.workers.ml_terminology_extractor', 279, f'İşlem Tamamlandı: {terms_file} [{action}]'))
            except Exception as e:
                logger.error(tr_log('core.workers.ml_terminology_extractor', 281, f'Terminoloji dosyası kaydedilemedi: {e}'))

def main():
    parser = argparse.ArgumentParser(description='Uzun Bağlam (Long-Context) ML-Tabanlı Terminoloji Çıkarma')
    parser.add_argument('--project-path', type=str, default='.', help='Projenin ana dizini yolu (varsayılan: ./)')
    parser.add_argument('--append', action='store_true', help='Mevcut terminology.json dosyasının üzerine yazmak yerine terimleri listeye ekle')
    args = parser.parse_args()
    extractor = MLTerminologyExtractor(args.project_path)
    extractor.run(append=args.append)
if __name__ == '__main__':
    main()