from core.localization import tr_log
from core.workers.text_utils import TextUtils
import os
import re
from PyQt6.QtCore import QObject, pyqtSignal
import json
import time
from logger import app_logger
KOREAN_PATTERN = re.compile('[\\uac00-\\ud7a3\\u1100-\\u11ff\\u3130-\\u318f]')
CHINESE_PATTERN = re.compile('[\\u4e00-\\u9fff]')
from core.workers.translation_quality_checker import TranslationQualityChecker

class TranslationWorker(QObject):
    """
    Dosya çeviri işlemini arayüzü dondurmadan arka planda yürüten işçi sınıfı.
    MCP entegrasyonu: LLMProvider üzerinden Gemini veya OpenAI-uyumlu servislerle çalışır.
    
    Translation Cache: Paragraf bazlı cache + fuzzy matching
    Terminology Memory: Otomatik terim çıkarma + prompt entegrasyonu
    """
    finished = pyqtSignal(bool)
    error = pyqtSignal(str)
    progress = pyqtSignal(int, int)
    request_made = pyqtSignal()

    def __init__(self, input_folder, output_folder, api_key, startpromt, model_version='gemini-2.5-flash', file_limit=None, max_retries=3, endpoint_id=None, endpoint_config=None, terminology_section='', project_path=None, cache_enabled=True, terminology_enabled=True, async_enabled=False, async_threads=3, batch_enabled=False, max_batch_chars=33000, max_chapters_per_batch=5, source_lang='en', translation_provider='llm'):
        super().__init__()
        self.input_folder = input_folder
        self.output_folder = output_folder
        self.api_key = api_key
        self.prompt_prefix = startpromt
        self.model_version = model_version
        self.file_limit = file_limit
        self.max_retries = max_retries
        self.is_running = True
        self.is_paused = False
        self.translation_errors = {}
        self.error_log_path = os.path.join(self.output_folder, 'translation_errors.json')
        self.shutdown_on_finish = False
        self.terminology_section = terminology_section
        self.source_lang = source_lang
        self.quality_checker = TranslationQualityChecker(source_lang=self.source_lang)
        self.project_path = project_path
        self.cache_enabled = cache_enabled
        self.terminology_enabled = terminology_enabled
        self.async_enabled = async_enabled
        self.async_threads = async_threads
        self.batch_enabled = batch_enabled
        self.max_batch_chars = max_batch_chars
        self.max_chapters_per_batch = max_chapters_per_batch
        import threading
        self.data_lock = threading.Lock()
        self.translated_count_session = 0
        self.global_error = None
        self._all_endpoints = []
        self._current_endpoint_idx = 0
        self._endpoint_exhausted = False
        self.api_request_count = 0
        self.api_token_count = 0
        self.cache_hit_count = 0
        self.cache_miss_count = 0
        self.paragraph_cache_hit_count = 0
        self.paragraph_cache_miss_count = 0
        self.translation_start_time = None
        self.translation_provider = translation_provider
        self.free_engine = None
        self.provider = None
        self.endpoint_id = endpoint_id
        self.endpoint_config = endpoint_config
        if self.translation_provider == 'llm':
            self._init_provider()
            self._load_all_endpoints()
        else:
            self._init_free_engine()
        self._cache = None
        self._terminology_manager = None

    def _save_translation_to_db(self, file_name: str, translated_file_path: str, status: str='Çevrildi'):
        """
        Çeviri tamamlandığında sonuçları veritabanına anında kaydeder.
        project_path tanımlanmamışsa sessizce atlar.
        """
        if not self.project_path:
            return
        try:
            from core.database_manager import DatabaseManager
            db_mgr = DatabaseManager(self.project_path)
            if not db_mgr.db_exists():
                return
            original_file_name = file_name
            original_file_path = os.path.join(self.input_folder, file_name)
            translated_file_name = os.path.basename(translated_file_path)
            sort_key = file_name.replace('.txt', '')
            file_dict = {'sort_key': sort_key, 'original_file_name': original_file_name, 'original_file_path': original_file_path, 'translated_file_name': translated_file_name, 'translated_file_path': translated_file_path, 'translation_status': status, 'is_translated': True, 'display_status': status}
            db_mgr.upsert_single_file(file_dict)
        except Exception as e:
            app_logger.warning(tr_log('core.workers.translation_worker', 133, f'DB anlık kayıt hatası ({file_name}): {e}'))

    @property
    def terminology_manager(self):
        return getattr(self, '_terminology_manager', None)

    def _init_provider(self):
        """LLMProvider'ı başlatır. Geriye uyumlu: endpoint yoksa doğrudan API key ile çalışır."""
        try:
            from core.llm_provider import LLMProvider
            if self.endpoint_config:
                self.provider = LLMProvider(endpoint=self.endpoint_config, api_key=self.api_key)
            elif self.endpoint_id:
                self.provider = LLMProvider(endpoint_id=self.endpoint_id)
            elif self.api_key:
                self.provider = LLMProvider(endpoint={'id': 'legacy_gemini', 'name': 'Eski Gemini', 'type': 'gemini', 'model_id': self.model_version, 'base_url': None, 'use_key_rotation': False, 'headers': {}}, api_key=self.api_key)
            else:
                self.provider = None
        except Exception as e:
            app_logger.error(tr_log('core.workers.translation_worker', 164, f'LLMProvider başlatılamadı: {e}'))
            self.provider = None

    def _init_free_engine(self):
        """Ücretsiz çeviri motorunu (Google/Yandex) başlatır."""
        try:
            from core.free_translators import FreeTranslationEngine
            self.free_engine = FreeTranslationEngine(provider_name=self.translation_provider, source_lang='auto', target_lang='tr', api_key=self.api_key or None)
            app_logger.info(tr_log('core.workers.translation_worker', 177, f'Ücretsiz çeviri motoru başlatıldı: {self.translation_provider}'))
        except Exception as e:
            app_logger.error(tr_log('core.workers.translation_worker', 179, f'Ücretsiz çeviri motoru başlatılamadı: {e}'))
            self.free_engine = None

    def _translate_with_free_translator(self, content_text: str) -> str | None:
        """
        Ücretsiz çeviri motoru ile metni çevirir.
        Paragraflar 4500 karakter sınırını geçmeyecek şekilde gruplanarak paket (batch) halinde gönderilir.
        """
        if not self.free_engine:
            app_logger.error(tr_log('core.workers.translation_worker', 188, 'Ücretsiz çeviri motoru başlatılmamış.'))
            return None
        if not content_text or not content_text.strip():
            return content_text
        paragraphs = [p for p in content_text.split('\n\n') if p.strip()]
        if not paragraphs:
            return content_text
        chunks = []
        current_chunk = []
        current_length = 0
        max_chunk_chars = 500
        for para in paragraphs:
            para_len = len(para)
            if para_len > max_chunk_chars:
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []
                    current_length = 0
                words = para.split(' ')
                sub_chunk = ''
                for word in words:
                    if len(sub_chunk) + len(word) + 1 > max_chunk_chars:
                        if sub_chunk:
                            chunks.append(sub_chunk.strip())
                        sub_chunk = word
                    else:
                        sub_chunk += ' ' + word if sub_chunk else word
                if sub_chunk:
                    chunks.append(sub_chunk.strip())
                continue
            added_len = para_len + (2 if current_chunk else 0)
            if current_length + added_len > max_chunk_chars:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_length = para_len
            else:
                current_chunk.append(para)
                current_length += added_len
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        translated_chunks = []
        retry_wait = 1.0
        for chunk in chunks:
            while self.is_paused and self.is_running:
                time.sleep(0.5)
            if not self.is_running:
                return None
            if not chunk.strip():
                continue
            success = False
            backoff = retry_wait
            for attempt in range(self.max_retries):
                try:
                    result = self.free_engine.translate(chunk)
                    if result is not None and isinstance(result, str):
                        translated_chunks.append(result)
                        success = True
                        break
                    elif result is None and (not any((c.isalnum() for c in chunk))):
                        translated_chunks.append(chunk)
                        success = True
                        break
                    else:
                        raise ValueError('Çeviri motoru None veya geçersiz veri döndürdü')
                except Exception as e:
                    err = str(e)
                    app_logger.warning(tr_log('core.workers.translation_worker', 280, f'Ücretsiz çeviri hatası (deneme {attempt + 1}/{self.max_retries}): {err}'))
                    if not self.is_running:
                        return None
                    sleep_start = time.time()
                    while time.time() - sleep_start < backoff:
                        if not self.is_running:
                            return None
                        time.sleep(0.3)
                    backoff = min(backoff * 2, 60)
            if not success:
                app_logger.error(tr_log('core.workers.translation_worker', 294, 'Ücretsiz çeviri maksimum deneme sayısını aştı; paket atlanıyor.'))
                translated_chunks.append(chunk)
            time.sleep(2)
        return '\n\n'.join(translated_chunks)

    def _load_all_endpoints(self):
        """
        Failover için kullanılabilir tüm endpoint'leri sıralı olarak yükler.
        Önce aktif provider'ın endpoint'i gelir, ardından diğerleri eklenir.
        Yalnızca API anahtarı mevcut olan endpoint'ler listeye alınır.
        """
        try:
            from core.llm_provider import load_endpoints, KeyPool
            data = load_endpoints()
            all_eps = data.get('endpoints', [])
            current_ep_id = getattr(self.provider, 'ep_id', None) if self.provider else None
            ordered = []
            for ep in all_eps:
                if ep.get('id') == current_ep_id:
                    ordered.insert(0, ep)
                else:
                    ordered.append(ep)
            if self.api_key and (not any((ep.get('id') == 'legacy_gemini' for ep in ordered))):
                ordered.append({'id': 'legacy_gemini', 'name': 'Proje API Anahtarı (Gemini)', 'type': 'gemini', 'model_id': self.model_version, 'base_url': None, 'use_key_rotation': False, 'headers': {}})
            valid = []
            for ep in ordered:
                ep_id = ep.get('id', '')
                if ep_id == 'legacy_gemini' and self.api_key:
                    valid.append(('legacy', ep, self.api_key))
                else:
                    pool = KeyPool(ep_id, ep.get('use_key_rotation', True))
                    if pool.has_keys():
                        valid.append(('pool', ep, None))
            self._all_endpoints = valid
            self._current_endpoint_idx = 0
            app_logger.info(tr_log('core.workers.translation_worker', 347, f"Endpoint failover listesi: {len(valid)} endpoint. Sıra: {[e[1].get('name', e[1].get('id')) for e in valid]}"))
        except Exception as e:
            app_logger.warning(tr_log('core.workers.translation_worker', 352, f'Endpoint listesi yüklenemedi: {e}'))
            self._all_endpoints = []

    def _try_next_endpoint(self, failed_at_idx: int) -> bool:
        """
        Compare-and-swap tabanlı thread-safe 429 kurtarma mekanizması.

        failed_at_idx: Bu thread hangi endpoint idx'indeyken 429 aldı?

        Adım 1 — Pool İçi Key Rotasyonu (öncelikli):
          Aynı endpoint'in havuzunda daha fazla anahtar varsa → sıradakine geç.
          Tüm pool anahtarları tükenmeden farklı endpoint'e geçilmez.

        Adım 2 — Endpoint Geçişi (pool tamamen tükendikten sonra):
          Tüm pool anahtarları denendiyse → bir sonraki MCP endpoint'ine geç.

        CAS koruması (thread-safe):
          _current_endpoint_idx != failed_at_idx ise başka thread zaten işledi,
          mevcut kaynağı kullanmaya devam et (ek geçiş YAPMA).

        Dönüş değeri:
          True  → Kaynak değiştirildi veya başka thread zaten değiştirdi (devam edebilir)
          False → Tüm kaynaklar (pool + endpoint'ler) tükendi (dur)
        """
        with self.data_lock:
            if self._endpoint_exhausted:
                return False
            if self._current_endpoint_idx != failed_at_idx:
                app_logger.info(tr_log('core.workers.translation_worker', 382, f'429 kurtarma: arayan idx={failed_at_idx}, mevcut idx={self._current_endpoint_idx} (başka thread zaten geçti). Mevcut kaynak ile devam.'))
                return True
            if self.provider and self.provider.rotate_key():
                return True
            next_idx = failed_at_idx + 1
            if next_idx >= len(self._all_endpoints):
                app_logger.warning(tr_log('core.workers.translation_worker', 396, f"Tüm endpoint'ler ve pool'ları tükendi ({failed_at_idx + 1}/{len(self._all_endpoints)}). Çeviri durduruluyor."))
                self._endpoint_exhausted = True
                return False
            (kind, ep, key) = self._all_endpoints[next_idx]
            try:
                from core.llm_provider import LLMProvider
                if kind == 'legacy':
                    new_provider = LLMProvider(endpoint=ep, api_key=key)
                else:
                    new_provider = LLMProvider(endpoint=ep)
                self.provider = new_provider
                self._current_endpoint_idx = next_idx
                app_logger.info(tr_log('core.workers.translation_worker', 413, f"Endpoint geçişi başarılı → {ep.get('name', ep.get('id', '?'))} (idx={next_idx}/{len(self._all_endpoints)})"))
                return True
            except Exception as e:
                app_logger.error(tr_log('core.workers.translation_worker', 419, f"Endpoint geçişi başarısız [{ep.get('id')}]: {e}"))
                self._current_endpoint_idx = next_idx
                return False

    def _init_cache_and_terminology(self):
        """Cache ve Terminology nesnelerini proje yoluna göre başlatır."""
        if self.project_path:
            if self.terminology_enabled:
                try:
                    from terminology.terminology_manager import TerminologyManager
                    self._terminology_manager = TerminologyManager(self.project_path)
                    if self._terminology_manager.needs_extraction() and self.provider:
                        app_logger.info(tr_log('core.workers.translation_worker', 437, 'Terminology listesi boş — otomatik terim çıkarma başlatılıyor...'))
                        sample_text = self._terminology_manager.get_sample_text_from_project()
                        if sample_text:
                            count = self._terminology_manager.auto_extract_terms(sample_text, self.provider)
                            if count > 0:
                                app_logger.info(tr_log('core.workers.translation_worker', 442, f'Otomatik terim çıkarma: {count} terim eklendi.'))
                            else:
                                app_logger.info(tr_log('core.workers.translation_worker', 444, 'Otomatik terim çıkarma: terim bulunamadı.'))
                        else:
                            app_logger.info(tr_log('core.workers.translation_worker', 446, 'Otomatik terim çıkarma: dwnld klasöründe örnek metin bulunamadı.'))
                    auto_section = self._terminology_manager.build_prompt_section()
                    if auto_section:
                        self.terminology_section = auto_section
                        app_logger.info(tr_log('core.workers.translation_worker', 452, f'Terminology Memory etkinleştirildi. {len(self._terminology_manager.terms)} terim yüklendi.'))
                    else:
                        app_logger.info(tr_log('core.workers.translation_worker', 454, 'Terminology Memory: terim yok, prompt bölümü eklenmedi.'))
                except Exception as e:
                    app_logger.warning(tr_log('core.workers.translation_worker', 456, f'Terminology Manager başlatılamadı: {e}'))
                    self._terminology_manager = None

    def pause(self):
        """Çeviriyi duraklatır."""
        self.is_paused = True

    def resume(self):
        """Çeviriyi devam ettirir."""
        self.is_paused = False

    def stop(self):
        """Çeviriyi durdurur."""
        self.is_running = False

    @staticmethod
    def _has_excessive_cjk(text, threshold=0.5):
        """Metnin Çince/Korece karakter oranının eşik değerini aşıp aşmadığını kontrol eder.
        Eşik varsayılan %50. True dönerse çeviri hatalı kabul edilir."""
        if not text:
            return False
        total_chars = len(text)
        if total_chars == 0:
            return False
        korean_count = len(KOREAN_PATTERN.findall(text))
        chinese_count = len(CHINESE_PATTERN.findall(text))
        cjk_ratio = (korean_count + chinese_count) / total_chars
        return cjk_ratio > threshold

    def is_translation_failed(self, original: str, translated: str, file_name: str='') -> bool:
        """Çevirinin kalite kontrol kriterlerini (CJK, benzerlik %80+, dil tespiti) karşılayıp karşılamadığını kontrol eder."""
        if hasattr(self, 'quality_checker') and self.quality_checker:
            return self.quality_checker.is_translation_failed(original, translated, file_name)
        return self._has_excessive_cjk(translated)

    # İnternet kopması / asılma durumunda API çağrısının bekleyeceği maksimum süre (saniye).
    API_CALL_TIMEOUT_SECONDS = 600  # 10 dakika

    def _call_api_with_timeout(self, full_prompt: str):
        """
        provider.generate() çağrısını ayrı bir daemon thread'de çalıştırır ve
        API_CALL_TIMEOUT_SECONDS süre içinde yanıt gelmezse TimeoutError fırlatır.

        Döndürür: API yanıt metni
        Fırlatır: TimeoutError (timeout), Exception (API hatası)
        """
        import threading
        result_box = [None]
        exc_box    = [None]

        def _worker():
            try:
                result_box[0] = self.provider.generate(full_prompt)
            except Exception as exc:
                exc_box[0] = exc

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

        elapsed = 0.0
        interval = 0.5
        while t.is_alive():
            if not self.is_running:
                return None  # kullanıcı durdurdu
            time.sleep(interval)
            elapsed += interval
            if elapsed >= self.API_CALL_TIMEOUT_SECONDS:
                raise TimeoutError(
                    f"API yaniti {self.API_CALL_TIMEOUT_SECONDS // 60} dakika icinde gelmedi "
                    f"(internet kesintisi olabilir). Istek yeniden denenecek."
                )

        if exc_box[0] is not None:
            raise exc_box[0]
        return result_box[0]

    def _call_api_with_retry(self, full_prompt: str) -> str | None:
        """
        Verilen prompt'u API'ye gönderir, retry + duraklatma/durdurma mantığıyla.
        Başarılı yanıtı string olarak döndürür; hata durumunda None döner.

        Timeout davranışı:
          - API_CALL_TIMEOUT_SECONDS (600 s = 10 dk) içinde yanıt gelmezse
            istek tekrarlanır (max_retries sınırı içinde).
        """
        retry_count = 0
        while retry_count < self.max_retries:
            while self.is_paused and self.is_running:
                time.sleep(0.5)
            if not self.is_running:
                return None
            with self.data_lock:
                my_ep_idx = self._current_endpoint_idx
            try:
                result = self._call_api_with_timeout(full_prompt)
                if result is None and not self.is_running:
                    return None  # kullanıcı durdurdu
                return result
            except TimeoutError as te:
                retry_count += 1
                app_logger.warning(tr_log(
                    'core.workers.translation_worker', 375,
                    f'API timeout (deneme {retry_count}/{self.max_retries}): {te}'
                ))
                if retry_count >= self.max_retries:
                    app_logger.error(tr_log(
                        'core.workers.translation_worker', 378,
                        f'API {self.max_retries} timeout sonrasi yanitlamadi. Dosya atlaniyor.'
                    ))
                    return None
                wait_time = min(30 * retry_count, 120)
                app_logger.info(tr_log(
                    'core.workers.translation_worker', 382,
                    f'Timeout sonrasi {wait_time}s bekleniyor, ardindan yeniden denenecek...'
                ))
                sleep_start = time.time()
                while time.time() - sleep_start < wait_time:
                    if not self.is_running:
                        return None
                    time.sleep(0.5)
            except Exception as e:
                last_error = str(e)
                if any((code in last_error for code in ['500', '503'])) and retry_count < self.max_retries - 1:
                    retry_count += 1
                    wait_time = min(2 ** retry_count, 60)
                    self.global_error = f'Sunucu hatasi. {wait_time}s sonra tekrar deneniyor. ({retry_count}/{self.max_retries})'
                    sleep_start = time.time()
                    while time.time() - sleep_start < wait_time:
                        if not self.is_running:
                            return None
                        time.sleep(0.5)
                elif '429' in last_error or 'ResourceExhausted' in last_error:
                    app_logger.warning(tr_log('core.workers.translation_worker', 520, f"429 / ResourceExhausted (EP idx={my_ep_idx}) — sonraki endpoint'e geciliyor..."))
                    if self._try_next_endpoint(my_ep_idx):
                        retry_count = 0
                        continue
                    else:
                        with self.data_lock:
                            self.global_error = "Tum API endpoint'leri tukendi. Ceviri durduruluyor."
                            self.is_running = False
                        return None
                else:
                    app_logger.warning(tr_log('core.workers.translation_worker', 530, f'API cagrisi basarisiz: {last_error}'))
                    return None
        return None


    def _translate_paragraphs(self, content: str) -> str | None:
        """
        Paragraf bazlı çeviri (cache kaldırıldı).
        Terminoloji terimleri API'ye gönderilmeden önce kaynak metne enjekte edilir.

        Tek paragraflı dosyalar için None döndürür → tam-dosya akışına geçilir.
        """
        paragraphs = TextUtils.split_into_paragraphs(content)
        if len(paragraphs) <= 1:
            return None
        PARA_SEP = '\n\n===PARAGRAPH_BREAK===\n\n'
        combined_text = PARA_SEP.join(paragraphs)
        if self._terminology_manager:
            combined_text = self._terminology_manager.build_injected_source(combined_text, source_lang=self.source_lang)
        full_prompt = self.prompt_prefix or ''
        if len(paragraphs) > 1:
            full_prompt += '\n\n[ÖNEMLİ: Metin paragraflar halinde verilmiştir. Her paragrafı ayrı ayrı çevir. Paragraflar arasındaki ===PARAGRAPH_BREAK=== ayırıcılarını çıktıda da koru.]\n\n'
        else:
            full_prompt += '\n\n'
        full_prompt += combined_text
        with self.data_lock:
            self.api_request_count += 1
        self.request_made.emit()
        translated_text = self._call_api_with_retry(full_prompt)
        if translated_text is None:
            return None
        if self._has_excessive_cjk(translated_text):
            app_logger.warning(tr_log('core.workers.translation_worker', 574, 'Paragraf bazlı çeviri CJK oranı yüksek.'))
            return None
        if len(paragraphs) > 1 and '===PARAGRAPH_BREAK===' in translated_text:
            translated_parts = re.split('\\s*===PARAGRAPH_BREAK===\\s*', translated_text)
        else:
            translated_parts = [translated_text]
        translated_parts = [p.strip() for p in translated_parts if p.strip()]
        if len(translated_parts) != len(paragraphs):
            app_logger.warning(tr_log('core.workers.translation_worker', 584, f'Paragraf sayı uyumsuzluğu: beklenen {len(paragraphs)}, alınan {len(translated_parts)}. Tek parça olarak işleniyor.'))
        return '\n\n'.join(translated_parts)

    def _translate_with_paragraph_cache(self, content: str) -> str | None:
        """
        [DEPRECATED] Geriye uyumluluk için korunur.
        Yeni kod _translate_paragraphs() kullanmalıdır.
        """
        return self._translate_paragraphs(content)

    def _process_single_file(self, i, file_name, total_files):
        while self.is_paused and self.is_running:
            import time
            time.sleep(0.5)
        if not self.is_running:
            return
        with self.data_lock:
            if self.file_limit is not None and self.translated_count_session >= self.file_limit:
                app_logger.info(tr_log('core.workers.translation_worker', 610, f'Belirlenen limit ({self.file_limit}) sayısına ulaşıldı.'))
                self.is_running = False
                return
        original_file_path = os.path.join(self.input_folder, file_name)
        translated_file_name = f'translated_{file_name}'
        translated_file_path = os.path.join(self.output_folder, translated_file_name)
        with self.data_lock:
            has_error = file_name in self.translation_errors
        if os.path.exists(translated_file_path) and (not has_error):
            self.progress.emit(i + 1, total_files)
            return
        try:
            with open(original_file_path, 'r', encoding='utf-8') as f:
                content_text = f.read()
        except Exception as e:
            with self.data_lock:
                self.translation_errors[file_name] = f'Okuma Hatası: {str(e)}'
            self.progress.emit(i + 1, total_files)
            return
        para_result = self._translate_paragraphs(content_text)
        if para_result is not None:
            if not self.is_translation_failed(content_text, para_result, file_name):
                with open(translated_file_path, 'w', encoding='utf-8') as f:
                    f.write(para_result)
                with self.data_lock:
                    self.translated_count_session += 1
                    if file_name in self.translation_errors:
                        del self.translation_errors[file_name]
                    if self.file_limit is not None and self.translated_count_session >= self.file_limit:
                        app_logger.info(tr_log('core.workers.translation_worker', 610, f'Belirlenen limit ({self.file_limit}) sayısına ulaşıldı.'))
                        self.is_running = False
                self._save_translation_to_db(file_name, translated_file_path, 'Çevrildi')
                app_logger.info(tr_log('core.workers.translation_worker', 645, f'Paragraf bazlı çeviri tamamlandı: {file_name}'))
                self.progress.emit(i + 1, total_files)
                return
            else:
                app_logger.warning(tr_log('core.workers.translation_worker', 649, f'Paragraf bazlı çeviri kalite kontrolünden geçemedi: {file_name}'))
        cached_translation = None
        if self._cache:
            cached_translation = self._cache.get_paragraph(content_text, self.model_version)
        if cached_translation is not None:
            if self.is_translation_failed(content_text, cached_translation, file_name):
                app_logger.warning(tr_log('core.workers.translation_worker', 658, f'Cache hit ancak kalite kontrol başarısız, cache atlanıyor: {file_name}'))
                try:
                    with self.data_lock:
                        self._cache.remove(content_text, self.model_version)
                except Exception:
                    pass
            else:
                with self.data_lock:
                    self.cache_hit_count += 1
                app_logger.info(tr_log('core.workers.translation_worker', 667, f'Cache hit: {file_name}'))
                with open(translated_file_path, 'w', encoding='utf-8') as f:
                    f.write(cached_translation)
                with self.data_lock:
                    self.translated_count_session += 1
                    if file_name in self.translation_errors:
                        del self.translation_errors[file_name]
                    if self.file_limit is not None and self.translated_count_session >= self.file_limit:
                        app_logger.info(tr_log('core.workers.translation_worker', 610, f'Belirlenen limit ({self.file_limit}) sayısına ulaşıldı.'))
                        self.is_running = False
                self._save_translation_to_db(file_name, translated_file_path, 'Çevrildi')
                self.progress.emit(i + 1, total_files)
                return
        if self._cache:
            with self.data_lock:
                self.cache_miss_count += 1
        if self.prompt_prefix:
            full_prompt = self.prompt_prefix
        else:
            full_prompt = ''
        if self.terminology_section:
            full_prompt += '\n\n' + self.terminology_section
        full_prompt += '\n\n' + content_text
        translated_text = None
        last_error = ''
        api_limit_hit = False
        retry_count = 0
        with self.data_lock:
            self.api_request_count += 1
        self.request_made.emit()
        while retry_count < self.max_retries:
            while self.is_paused and self.is_running:
                import time
                time.sleep(0.5)
            if not self.is_running:
                break
            with self.data_lock:
                my_ep_idx = self._current_endpoint_idx
            try:
                translated_text = self.provider.generate(full_prompt)
                with self.data_lock:
                    if file_name in self.translation_errors:
                        del self.translation_errors[file_name]
                break
            except Exception as e:
                last_error = str(e)
                if any((code in last_error for code in ['500', '503'])) and retry_count < self.max_retries - 1:
                    retry_count += 1
                    wait_time = min(2 ** retry_count, 60)
                    self.global_error = f'Sunucu hatası ({last_error}). {wait_time} saniye sonra tekrar denenecek. Deneme Sayısı: {retry_count}/{self.max_retries}'
                    import time
                    sleep_start = time.time()
                    while time.time() - sleep_start < wait_time:
                        if not self.is_running:
                            break
                        time.sleep(0.5)
                elif '429' in last_error or 'ResourceExhausted' in last_error:
                    app_logger.warning(tr_log('core.workers.translation_worker', 729, f"429 / ResourceExhausted [{file_name}] (EP idx={my_ep_idx}) — sonraki endpoint'e geçiliyor..."))
                    if self._try_next_endpoint(my_ep_idx):
                        retry_count = 0
                        continue
                    else:
                        with self.data_lock:
                            self.global_error = "Tüm API endpoint'leri tükendi. Çeviri durduruluyor."
                            self.is_running = False
                        api_limit_hit = True
                        with self.data_lock:
                            self.translation_errors[file_name] = f'Kota Aşıldı: {last_error}'
                        try:
                            with open(translated_file_path, 'w', encoding='utf-8') as f:
                                f.write(f'Çeviri hatası (Kota aşıldı): {last_error}\n\nOrijinal Metin:\n{content_text[:500]}...')
                        except:
                            pass
                        break
                else:
                    with self.data_lock:
                        self.translation_errors[file_name] = f'Çeviri Hatası: {last_error}'
                    try:
                        with open(translated_file_path, 'w', encoding='utf-8') as f:
                            f.write(f'Çeviri hatası: {last_error}\n\nOrijinal Metin:\n{content_text[:500]}...')
                    except:
                        pass
                    break
        if not self.is_running:
            return
        if translated_text is not None:
            if self.is_translation_failed(content_text, translated_text, file_name):
                app_logger.warning(tr_log('core.workers.translation_worker', 761, f'Çeviri sonucu kalite kontrolünden geçemedi: {file_name}'))
                with self.data_lock:
                    self.translation_errors[file_name] = 'Çeviri Hatası: Çeviri kalite kontrol başarısız (çevrilmemiş metin / benzerlik >= %80 / CJK)'
            else:
                with open(translated_file_path, 'w', encoding='utf-8') as f:
                    f.write(translated_text)
                with self.data_lock:
                    self.translated_count_session += 1
                    if self.file_limit is not None and self.translated_count_session >= self.file_limit:
                        app_logger.info(tr_log('core.workers.translation_worker', 610, f'Belirlenen limit ({self.file_limit}) sayısına ulaşıldı.'))
                        self.is_running = False
                self._save_translation_to_db(file_name, translated_file_path, 'Çevrildi')
                if self._cache:
                    try:
                        with self.data_lock:
                            self._cache.set_paragraph(content_text, self.model_version, translated_text)
                    except Exception as e:
                        app_logger.warning(tr_log('core.workers.translation_worker', 777, f'Cache yazma hatası: {e}'))
        self.progress.emit(i + 1, total_files)

    def build_batches(self, files: list[str]) -> list[list[str]]:
        """
        Dosya listesini maxBatchChars ve maxChaptersPerBatch limitine
        göre batch'lere böler.

        Her eleman batch: [dosya_adı_1, dosya_adı_2, ...]
        """
        batches = []
        current_batch = []
        current_chars = 0
        for file_name in files:
            file_path = os.path.join(self.input_folder, file_name)
            try:
                file_size = os.path.getsize(file_path)
            except OSError:
                file_size = 0
            if current_batch and (current_chars + file_size > self.max_batch_chars or len(current_batch) >= self.max_chapters_per_batch):
                batches.append(current_batch)
                current_batch = []
                current_chars = 0
            current_batch.append(file_name)
            current_chars += file_size
        if current_batch:
            batches.append(current_batch)
        return batches

    def format_batch_input(self, batch: list[str], contents: dict[str, str]) -> str:
        """
        Dosya içeriklerini ===CHAPTER_START=== / ===CHAPTER_END=== ayraçlarıyla sarar.
        contents: {dosya_adı: içerik_metni}
        """
        parts = []
        for file_name in batch:
            content = contents.get(file_name, '')
            parts.append(f'===CHAPTER_START===\n{content.strip()}\n===CHAPTER_END===')
        return '\n\n'.join(parts)

    def parse_batch_response(self, response: str, batch: list[str], contents: dict[str, str]) -> dict[str, str]:
        """
        API yanıtını ===CHAPTER_START=== / ===CHAPTER_END=== ayraçlarıyla parse eder.
        Bölümler index sırasıyla batch listesine eşleştirilir.
        Parse edilen her bölüm paragraf bazlı cache'e yazılır.

        Returns: {dosya_adı: çevrilmiş_içerik} — sadece başarıyla parse edilenler.
        """
        pattern = re.compile('===CHAPTER_START===(.*?)===CHAPTER_END===', re.DOTALL)
        parsed_blocks = pattern.findall(response)
        result = {}
        for (i, file_name) in enumerate(batch):
            if i >= len(parsed_blocks):
                break
            chapter_text = parsed_blocks[i].strip()
            if not chapter_text:
                continue
            if self._has_excessive_cjk(chapter_text):
                app_logger.warning(tr_log('core.workers.translation_worker', 856, f'Batch parse: CJK oranı yüksek, atlanıyor — {file_name}'))
                continue
            result[file_name] = chapter_text
        app_logger.info(tr_log('core.workers.translation_worker', 862, f'Batch parse: {len(result)}/{len(batch)} bölüm parse edildi.'))
        return result

    def _process_batch(self, batch: list[str], batch_idx: int, total_batches: int) -> list[str]:
        """
        Tek bir batch'i işler:
          1. İçerikleri oku
          2. Batch formatla
          3. API'ye gönder
          4. Parse et
          5. Başarılı olanları kaydet
          6. Başarısız olanlar fallback'e gider

        Returns: Başarısız kalan dosya adları listesi (boş liste = tam başarı)
        """
        while self.is_paused and self.is_running:
            time.sleep(0.5)
        if not self.is_running:
            return batch
        with self.data_lock:
            if self.file_limit is not None and self.translated_count_session >= self.file_limit:
                app_logger.info(tr_log('core.workers.translation_worker', 610, f'Belirlenen limit ({self.file_limit}) sayısına ulaşıldı.'))
                self.is_running = False
                return []
        app_logger.info(tr_log('core.workers.translation_worker', 884, f'Batch {batch_idx + 1}/{total_batches}: {len(batch)} dosya işleniyor — {batch}'))
        contents = {}
        unreadable = []
        for file_name in batch:
            file_path = os.path.join(self.input_folder, file_name)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    contents[file_name] = f.read()
            except Exception as e:
                app_logger.error(tr_log('core.workers.translation_worker', 895, f'Batch okuma hatası [{file_name}]: {e}'))
                with self.data_lock:
                    self.translation_errors[file_name] = f'Okuma Hatası: {e}'
                unreadable.append(file_name)
        readable_batch = [f for f in batch if f not in unreadable]
        if not readable_batch:
            return []
        batch_input = self.format_batch_input(readable_batch, contents)
        full_prompt = self.prompt_prefix or ''
        if self.terminology_section:
            full_prompt += '\n\n' + self.terminology_section
        full_prompt += '\n\n[ÖNEMLİ: Aşağıda birden fazla bölüm verilmiştir. Her bölümü ===CHAPTER_START=== ile başlayan ve ===CHAPTER_END=== ile biten bloklar halinde ayrı ayrı çevir. Ayraçları ve sıralamayı kesinlikle koru.]\n\n'
        full_prompt += batch_input
        with self.data_lock:
            self.api_request_count += 1
        self.request_made.emit()
        response = self._call_api_with_retry(full_prompt)
        if response is None:
            app_logger.warning(tr_log('core.workers.translation_worker', 923, f'Batch {batch_idx + 1}: API yanıtı alınamadı.'))
            return readable_batch
        parsed = self.parse_batch_response(response, readable_batch, contents)
        failed = []
        if len(parsed) == 0:
            app_logger.warning(tr_log('core.workers.translation_worker', 932, f'Batch {batch_idx + 1}: Parse başarısız. Batch bölünüyor...'))
            return self._fallback_split_batch(readable_batch, batch_idx, total_batches)
        for (file_name, chapter_text) in parsed.items():
            with self.data_lock:
                if self.file_limit is not None and self.translated_count_session >= self.file_limit:
                    app_logger.info(tr_log('core.workers.translation_worker', 1093, f'Belirlenen limit ({self.file_limit}) sayısına ulaşıldı.'))
                    self.is_running = False
                    break
            translated_file_path = os.path.join(self.output_folder, f'translated_{file_name}')
            try:
                with open(translated_file_path, 'w', encoding='utf-8') as f:
                    f.write(chapter_text)
                with self.data_lock:
                    self.translated_count_session += 1
                    if file_name in self.translation_errors:
                        del self.translation_errors[file_name]
                    if self.file_limit is not None and self.translated_count_session >= self.file_limit:
                        app_logger.info(tr_log('core.workers.translation_worker', 1093, f'Belirlenen limit ({self.file_limit}) sayısına ulaşıldı.'))
                        self.is_running = False
                app_logger.info(tr_log('core.workers.translation_worker', 945, f'Batch çeviri kaydedildi: {file_name}'))
                if not self.is_running:
                    break
            except Exception as e:
                app_logger.error(tr_log('core.workers.translation_worker', 947, f'Batch kaydetme hatası [{file_name}]: {e}'))
                failed.append(file_name)
        for file_name in readable_batch:
            if file_name not in parsed:
                failed.append(file_name)
        return failed

    def _fallback_split_batch(self, batch: list[str], batch_idx: int, total_batches: int) -> list[str]:
        """
        Parse başarısız olan batch'i ikiye bölerek tekrar dener.
        İkiye bölme de başarısız olursa dosyaları fallback listesine ekler.
        """
        if len(batch) <= 1:
            return batch
        mid = len(batch) // 2
        first_half = batch[:mid]
        second_half = batch[mid:]
        app_logger.info(tr_log('core.workers.translation_worker', 970, f'Batch bölünüyor: {first_half} | {second_half}'))
        failed = []
        for half in [first_half, second_half]:
            if len(half) == 1:
                self._process_single_file(0, half[0], 1)
            else:
                sub_failed = self._process_batch(half, batch_idx, total_batches)
                failed.extend(sub_failed)
        return failed

    def _run_batch_mode(self, files_to_translate: list[str], total_files: int):
        """
        Batch modunda tüm çeviri döngüsünü yürütür.
        Başarısız kalan dosyalar _process_single_file() ile tek tek işlenir.
        """
        app_logger.info(tr_log('core.workers.translation_worker', 988, f'Batch Çeviri başlatılıyor. Toplam: {total_files} dosya, maxBatchChars={self.max_batch_chars}, maxChaptersPerBatch={self.max_chapters_per_batch}'))
        pending = []
        for file_name in files_to_translate:
            translated_path = os.path.join(self.output_folder, f'translated_{file_name}')
            with self.data_lock:
                has_error = file_name in self.translation_errors
            if os.path.exists(translated_path) and (not has_error):
                self.progress.emit(files_to_translate.index(file_name) + 1, total_files)
            else:
                pending.append(file_name)
        if self.file_limit is not None:
            with self.data_lock:
                rem_limit = max(0, self.file_limit - self.translated_count_session)
            if rem_limit == 0:
                app_logger.info(tr_log('core.workers.translation_worker', 610, f'Belirlenen limit ({self.file_limit}) sayısına ulaşıldı.'))
                self.is_running = False
                return
            pending = pending[:rem_limit]
        batches = self.build_batches(pending)
        app_logger.info(tr_log('core.workers.translation_worker', 1005, f'Batch Çeviri: {len(pending)} dosya, {len(batches)} batch oluşturuldu.'))
        _progress_counter = [total_files - len(pending)]

        def _run_single_batch(args):
            """Tek bir batch'i işler: API çağrısı + fallback. Async executor ile uyumlu."""
            (batch_idx, batch) = args
            with self.data_lock:
                if not self.is_running:
                    return
                if self.file_limit is not None and self.translated_count_session >= self.file_limit:
                    self.is_running = False
                    return
            failed = self._process_batch(batch, batch_idx, len(batches))
            with self.data_lock:
                _progress_counter[0] += len(batch)
                cur_progress = _progress_counter[0]
            self.progress.emit(cur_progress, total_files)
            for file_name in failed:
                if not self.is_running:
                    break
                app_logger.info(tr_log('core.workers.translation_worker', 1023, f'Batch fallback → tekli çeviri: {file_name}'))
                idx = files_to_translate.index(file_name) if file_name in files_to_translate else 0
                self._process_single_file(idx, file_name, total_files)
        if self.async_enabled and len(batches) > 1:
            import concurrent.futures
            app_logger.info(tr_log('core.workers.translation_worker', 1030, f'Batch Async Modu: {self.async_threads} thread ile {len(batches)} batch paralel işleniyor.'))
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.async_threads) as executor:
                future_to_idx = {executor.submit(_run_single_batch, (batch_idx, batch)): batch_idx for (batch_idx, batch) in enumerate(batches) if self.is_running}
                for fut in concurrent.futures.as_completed(future_to_idx):
                    b_idx = future_to_idx[fut]
                    try:
                        fut.result()
                    except Exception as be:
                        app_logger.error(tr_log('core.workers.translation_worker', 1045, f'Batch async hatası [batch {b_idx}]: {be}'))
                    if not self.is_running:
                        break
        else:
            if self.async_enabled:
                app_logger.info(tr_log('core.workers.translation_worker', 1051, 'Batch Async Modu: Yalnızca 1 batch var, sıralı işleniyor.'))
            for (batch_idx, batch) in enumerate(batches):
                if not self.is_running:
                    break
                _run_single_batch((batch_idx, batch))
        app_logger.info(tr_log('core.workers.translation_worker', 1057, 'Batch Çeviri tamamlandı.'))

    def _run_free_translation(self):
        """
        Ücretsiz çeviri motoru (Google/Yandex) ile sıralı dosya çevirisi yapar.
        LLM'e özgü: prompt, cache (paragraf), batch, async modlar KULLANILMAZ.
        """
        self.translation_start_time = time.time()
        if os.path.exists(self.error_log_path):
            try:
                with open(self.error_log_path, 'r', encoding='utf-8') as f:
                    self.translation_errors = json.load(f)
            except Exception:
                self.translation_errors = {}
        try:
            time.sleep(0.5)
            files_to_translate = sorted([f for f in os.listdir(self.input_folder) if f.endswith('.txt')])
            total_files = len(files_to_translate)
            self.translated_count_session = 0
            app_logger.info(tr_log('core.workers.translation_worker', 1080, f'Ücretsiz Çeviri ({self.translation_provider}) başlatılıyor. Toplam: {total_files} dosya.'))
            for (i, file_name) in enumerate(files_to_translate):
                while self.is_paused and self.is_running:
                    time.sleep(0.5)
                if not self.is_running:
                    app_logger.info(tr_log('core.workers.translation_worker', 1089, f'Ücretsiz çeviri durduruldu: {i}/{total_files}'))
                    break
                if self.file_limit is not None and self.translated_count_session >= self.file_limit:
                    app_logger.info(tr_log('core.workers.translation_worker', 1093, f'Belirlenen limit ({self.file_limit}) sayısına ulaşıldı.'))
                    break
                original_file_path = os.path.join(self.input_folder, file_name)
                translated_file_name = f'translated_{file_name}'
                translated_file_path = os.path.join(self.output_folder, translated_file_name)
                with self.data_lock:
                    has_error = file_name in self.translation_errors
                if os.path.exists(translated_file_path) and (not has_error):
                    self.progress.emit(i + 1, total_files)
                    continue
                try:
                    with open(original_file_path, 'r', encoding='utf-8') as f:
                        content_text = f.read()
                except Exception as e:
                    with self.data_lock:
                        self.translation_errors[file_name] = f'Okuma Hatası: {str(e)}'
                    self.progress.emit(i + 1, total_files)
                    continue
                translated_text = self._translate_with_free_translator(content_text)
                if not self.is_running:
                    break
                if translated_text is not None:
                    try:
                        with open(translated_file_path, 'w', encoding='utf-8') as f:
                            f.write(translated_text)
                        with self.data_lock:
                            self.translated_count_session += 1
                            if file_name in self.translation_errors:
                                del self.translation_errors[file_name]
                        app_logger.info(tr_log('core.workers.translation_worker', 1130, f'Ücretsiz çeviri kaydedildi: {file_name}'))
                    except Exception as e:
                        with self.data_lock:
                            self.translation_errors[file_name] = f'Yazma Hatası: {str(e)}'
                else:
                    with self.data_lock:
                        self.translation_errors[file_name] = 'Çeviri Hatası: Boş sonuç'
                self.progress.emit(i + 1, total_files)
        except Exception as e:
            import traceback
            app_logger.critical(tr_log('core.workers.translation_worker', 1142, f'Ücretsiz Çeviri Kritik Hata: {type(e).__name__}: {e}\n{traceback.format_exc()}'))
            try:
                self.error.emit(f'Genel hata: {type(e).__name__}: {e}')
            except RuntimeError:
                pass
        finally:
            try:
                with open(self.error_log_path, 'w', encoding='utf-8') as f:
                    json.dump(self.translation_errors, f, indent=4, ensure_ascii=False)
            except Exception:
                pass
            app_logger.info(tr_log('core.workers.translation_worker', 1156, 'Ücretsiz Çeviri: finished sinyali gönderiliyor...'))
            try:
                self.finished.emit(self.shutdown_on_finish)
            except RuntimeError as e:
                app_logger.error(tr_log('core.workers.translation_worker', 1160, f'Ücretsiz Çeviri: finished.emit sonrası RuntimeError: {e}'))

    def run(self):
        if self.translation_provider == 'llm' and (not self.provider):
            self.error.emit('LLM sağlayıcı yapılandırılmamış. API anahtarı veya endpoint ayarlarını kontrol edin.')
            self.finished.emit(self.shutdown_on_finish)
            return
        if self.translation_provider != 'llm' and (not self.free_engine):
            self.error.emit(f'Ücretsiz çeviri motoru ({self.translation_provider}) başlatılamadı. deep-translator kütüphanesinin yüklü olduğundan emin olun: pip install deep-translator')
            self.finished.emit(self.shutdown_on_finish)
            return
        if self.translation_provider != 'llm':
            self._run_free_translation()
            return
        self.translation_start_time = time.time()
        self._init_cache_and_terminology()
        if os.path.exists(self.error_log_path):
            try:
                with open(self.error_log_path, 'r', encoding='utf-8') as f:
                    self.translation_errors = json.load(f)
            except:
                self.translation_errors = {}
        try:
            time.sleep(0.5)
            files_to_translate = sorted([f for f in os.listdir(self.input_folder) if f.endswith('.txt')])
            total_files = len(files_to_translate)
            self.translated_count_session = 0
            if self.batch_enabled:
                self._run_batch_mode(files_to_translate, total_files)
            elif self.async_enabled:
                import concurrent.futures
                app_logger.info(tr_log('core.workers.translation_worker', 1208, f'Asenkron Çeviri: {self.async_threads} thread ile başlatılıyor. Toplam dosya: {total_files}'))
                executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.async_threads)
                futures = {}
                try:
                    for (i, file_name) in enumerate(files_to_translate):
                        if not self.is_running:
                            app_logger.warning(tr_log('core.workers.translation_worker', 1216, f'Async: is_running=False — görev gönderimi durduruldu ({i}/{total_files})'))
                            break
                        fut = executor.submit(self._process_single_file, i, file_name, total_files)
                        futures[fut] = file_name
                    app_logger.info(tr_log('core.workers.translation_worker', 1221, f'Async: {len(futures)} görev gönderildi, tamamlanmaları bekleniyor...'))
                    for fut in concurrent.futures.as_completed(futures):
                        fname = futures[fut]
                        try:
                            fut.result()
                            app_logger.debug(tr_log('core.workers.translation_worker', 1227, f'Async: Görev tamamlandı — {fname}'))
                        except Exception as thread_e:
                            app_logger.error(tr_log('core.workers.translation_worker', 1229, f'Async Thread İstisnası [{fname}]: {type(thread_e).__name__}: {thread_e}'))
                        if not self.is_running:
                            app_logger.warning(tr_log('core.workers.translation_worker', 1232, 'Async: is_running=False — kalan görevler beklenecek, yeni görev gönderilmeyecek'))
                            break
                finally:
                    app_logger.info(tr_log('core.workers.translation_worker', 1237, "Async: Executor kapatılıyor (tüm thread'ler bekleniyor)..."))
                    executor.shutdown(wait=True, cancel_futures=False)
                    app_logger.info(tr_log('core.workers.translation_worker', 1239, 'Async: Executor tamamen kapandı.'))
            else:
                app_logger.info(tr_log('core.workers.translation_worker', 1242, 'Klasik (Ardışık) Çeviri başlatılıyor.'))
                for (i, file_name) in enumerate(files_to_translate):
                    if not self.is_running:
                        app_logger.info(tr_log('core.workers.translation_worker', 1245, f'Sıralı çeviri durduruldu: {i}/{total_files}'))
                        break
                    self._process_single_file(i, file_name, total_files)
        except Exception as e:
            import traceback
            app_logger.critical(tr_log('core.workers.translation_worker', 1251, f'TranslationWorker Kritik Hata: {type(e).__name__}: {e}\n{traceback.format_exc()}'))
            try:
                self.error.emit(f'Genel hata: {type(e).__name__}: {e}')
            except RuntimeError:
                pass
        finally:
            app_logger.info(tr_log('core.workers.translation_worker', 1257, f"TranslationWorker: finally bloğu — global_error={('var' if self.global_error else 'yok')}, is_running={self.is_running}"))
            if self.global_error:
                try:
                    app_logger.error(tr_log('core.workers.translation_worker', 1261, f'TranslationWorker: Global hata sinyali gönderiliyor — {self.global_error}'))
                    self.error.emit(self.global_error)
                except RuntimeError as e:
                    app_logger.error(tr_log('core.workers.translation_worker', 1264, f'TranslationWorker: error.emit sonrası RuntimeError (bekleniyor): {e}'))
            if self._cache:
                elapsed = time.time() - self.translation_start_time if self.translation_start_time else 0
                app_logger.info(tr_log('core.workers.translation_worker', 1269, f'Cache istatistikleri — Dosya Hit: {self.cache_hit_count}, Dosya Miss: {self.cache_miss_count}, Paragraf Hit: {self.paragraph_cache_hit_count}, Paragraf Miss: {self.paragraph_cache_miss_count}, API çağrısı: {self.api_request_count}, Süre: {elapsed:.1f}s'))
            try:
                with open(self.error_log_path, 'w', encoding='utf-8') as f:
                    json.dump(self.translation_errors, f, indent=4, ensure_ascii=False)
            except:
                pass
            app_logger.info(tr_log('core.workers.translation_worker', 1284, 'TranslationWorker: finished sinyali gönderiliyor...'))
            try:
                self.finished.emit(self.shutdown_on_finish)
            except RuntimeError as e:
                app_logger.error(tr_log('core.workers.translation_worker', 1288, f'TranslationWorker: finished.emit sonrası RuntimeError: {e}'))