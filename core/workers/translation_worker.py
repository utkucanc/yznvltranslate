import os
import re
from PyQt6.QtCore import QObject, pyqtSignal
import json
import time
from logger import app_logger

# Unicode aralıkları (translation_error_check_worker.py ile uyumlu)
KOREAN_PATTERN = re.compile(r'[\uac00-\ud7a3\u1100-\u11ff\u3130-\u318f]')
CHINESE_PATTERN = re.compile(r'[\u4e00-\u9fff]')

class TranslationWorker(QObject):
    """
    Dosya çeviri işlemini arayüzü dondurmadan arka planda yürüten işçi sınıfı.
    MCP entegrasyonu: LLMProvider üzerinden Gemini veya OpenAI-uyumlu servislerle çalışır.
    
    Translation Cache: Paragraf bazlı cache + fuzzy matching
    Terminology Memory: Otomatik terim çıkarma + prompt entegrasyonu
    """
    finished = pyqtSignal(bool)  # Kapatma durumu için bool
    error = pyqtSignal(str)
    progress = pyqtSignal(int, int)
    request_made = pyqtSignal()

    def __init__(self, input_folder, output_folder, api_key, startpromt,
                 model_version="gemini-2.5-flash",
                 file_limit=None, max_retries=3,
                 endpoint_id=None, endpoint_config=None,
                 terminology_section="",
                 project_path=None, cache_enabled=True, terminology_enabled=True,
                 async_enabled=False, async_threads=3,
                 batch_enabled=False, max_batch_chars=33000, max_chapters_per_batch=5):
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
        self.terminology_section = terminology_section  # Eski uyumluluk (manuel)

        # Otomatik özellikler
        self.project_path = project_path
        self.cache_enabled = cache_enabled
        self.terminology_enabled = terminology_enabled
        self.async_enabled = async_enabled
        self.async_threads = async_threads

        # Batch modu parametreleri
        self.batch_enabled = batch_enabled
        self.max_batch_chars = max_batch_chars
        self.max_chapters_per_batch = max_chapters_per_batch

        import threading
        self.data_lock = threading.Lock()
        self.translated_count_session = 0
        self.global_error = None

        # Endpoint failover
        self._all_endpoints = []   # [(kind, endpoint_dict, api_key_or_None), ...]
        self._current_endpoint_idx = 0
        self._endpoint_exhausted = False

        # İstatistik takibi (status bar için)
        self.api_request_count = 0
        self.api_token_count = 0
        self.cache_hit_count = 0
        self.cache_miss_count = 0
        self.paragraph_cache_hit_count = 0
        self.paragraph_cache_miss_count = 0
        self.translation_start_time = None

        # LLM Provider (MCP entegrasyonu)
        self.provider = None
        self.endpoint_id = endpoint_id
        self.endpoint_config = endpoint_config
        self._init_provider()
        self._load_all_endpoints()

        # Cache & Terminology nesneleri (run() içinde başlatılır)
        self._cache = None
        self._terminology_manager = None

    def _init_provider(self):
        """LLMProvider'ı başlatır. Geriye uyumlu: endpoint yoksa doğrudan API key ile çalışır."""
        try:
            from core.llm_provider import LLMProvider
            if self.endpoint_config:
                self.provider = LLMProvider(endpoint=self.endpoint_config, api_key=self.api_key)
            elif self.endpoint_id:
                self.provider = LLMProvider(endpoint_id=self.endpoint_id)
            elif self.api_key:
                # Geriye uyumluluk: eski Gemini yöntemi
                self.provider = LLMProvider(
                    endpoint={
                        "id": "legacy_gemini",
                        "name": "Eski Gemini",
                        "type": "gemini",
                        "model_id": self.model_version,
                        "base_url": None,
                        "use_key_rotation": False,
                        "headers": {}
                    },
                    api_key=self.api_key
                )
            else:
                self.provider = None
        except Exception as e:
            app_logger.error(f"LLMProvider başlatılamadı: {e}")
            self.provider = None

    def _load_all_endpoints(self):
        """
        Failover için kullanılabilir tüm endpoint'leri sıralı olarak yükler.
        Önce aktif provider'ın endpoint'i gelir, ardından diğerleri eklenir.
        Yalnızca API anahtarı mevcut olan endpoint'ler listeye alınır.
        """
        try:
            from core.llm_provider import load_endpoints, KeyPool
            data = load_endpoints()
            all_eps = data.get("endpoints", [])
            current_ep_id = getattr(self.provider, 'ep_id', None) if self.provider else None

            # Aktif endpoint'i ilk sıraya koy, geri kalanını ekle
            ordered = []
            for ep in all_eps:
                if ep.get("id") == current_ep_id:
                    ordered.insert(0, ep)
                else:
                    ordered.append(ep)

            # Legacy (proje config) API key ile Gemini endpoint (listede yoksa ekle)
            if self.api_key and not any(ep.get("id") == "legacy_gemini" for ep in ordered):
                ordered.append({
                    "id": "legacy_gemini",
                    "name": "Proje API Anahtarı (Gemini)",
                    "type": "gemini",
                    "model_id": self.model_version,
                    "base_url": None,
                    "use_key_rotation": False,
                    "headers": {}
                })

            # Yalnızca API anahtarı olan endpoint'leri al
            valid = []
            for ep in ordered:
                ep_id = ep.get("id", "")
                if ep_id == "legacy_gemini" and self.api_key:
                    valid.append(("legacy", ep, self.api_key))
                else:
                    pool = KeyPool(ep_id, ep.get("use_key_rotation", True))
                    if pool.has_keys():
                        valid.append(("pool", ep, None))

            self._all_endpoints = valid
            self._current_endpoint_idx = 0
            app_logger.info(
                f"Endpoint failover listesi: {len(valid)} endpoint. "
                f"Sıra: {[e[1].get('name', e[1].get('id')) for e in valid]}"
            )
        except Exception as e:
            app_logger.warning(f"Endpoint listesi yüklenemedi: {e}")
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

            # Başka bir thread zaten bu endpoint'ten atladı — yeni geçiş YAPMA
            if self._current_endpoint_idx != failed_at_idx:
                app_logger.info(
                    f"429 kurtarma: arayan idx={failed_at_idx}, "
                    f"mevcut idx={self._current_endpoint_idx} "
                    "(başka thread zaten geçti). Mevcut kaynak ile devam."
                )
                return True

            # ── Adım 1: Aynı endpoint'in pool'unda sıradaki anahtara geç ──
            if self.provider and self.provider.rotate_key():
                return True  # Pool içi rotasyon başarılı; log rotate_key() içinde yapılır

            # ── Adım 2: Pool tükendi → bir sonraki MCP endpoint'ine geç ──
            next_idx = failed_at_idx + 1
            if next_idx >= len(self._all_endpoints):
                app_logger.warning(
                    f"Tüm endpoint'ler ve pool'ları tükendi "
                    f"({failed_at_idx + 1}/{len(self._all_endpoints)}). "
                    "Çeviri durduruluyor."
                )
                self._endpoint_exhausted = True
                return False

            kind, ep, key = self._all_endpoints[next_idx]
            try:
                from core.llm_provider import LLMProvider
                if kind == "legacy":
                    new_provider = LLMProvider(endpoint=ep, api_key=key)
                else:
                    new_provider = LLMProvider(endpoint=ep)
                self.provider = new_provider
                self._current_endpoint_idx = next_idx
                app_logger.info(
                    f"Endpoint geçişi başarılı → {ep.get('name', ep.get('id', '?'))} "
                    f"(idx={next_idx}/{len(self._all_endpoints)})"
                )
                return True
            except Exception as e:
                app_logger.error(f"Endpoint geçişi başarısız [{ep.get('id')}]: {e}")
                # Oluşturulamayan endpoint'i de geç, bir sonrakini dene
                self._current_endpoint_idx = next_idx
                return False


    def _init_cache_and_terminology(self):
        """Cache ve Terminology nesnelerini proje yoluna göre başlatır."""
        if self.project_path:
            if self.cache_enabled:
                try:
                    from cache.translation_cache import TranslationCache
                    self._cache = TranslationCache(self.project_path)
                    stats = self._cache.stats()
                    app_logger.info(f"Translation Cache etkinleştirildi. Mevcut kayıt: {stats['entries']}")
                except Exception as e:
                    app_logger.warning(f"Translation Cache başlatılamadı: {e}")
                    self._cache = None

            if self.terminology_enabled:
                try:
                    from terminology.terminology_manager import TerminologyManager
                    self._terminology_manager = TerminologyManager(self.project_path)

                    # Otomatik terim çıkarma: terim listesi boşsa LLM ile çıkar
                    if self._terminology_manager.needs_extraction() and self.provider:
                        app_logger.info("Terminology listesi boş — otomatik terim çıkarma başlatılıyor...")
                        sample_text = self._terminology_manager.get_sample_text_from_project()
                        if sample_text:
                            count = self._terminology_manager.auto_extract_terms(sample_text, self.provider)
                            if count > 0:
                                app_logger.info(f"Otomatik terim çıkarma: {count} terim eklendi.")
                            else:
                                app_logger.info("Otomatik terim çıkarma: terim bulunamadı.")
                        else:
                            app_logger.info("Otomatik terim çıkarma: dwnld klasöründe örnek metin bulunamadı.")

                    # Terminology section oluştur
                    auto_section = self._terminology_manager.build_prompt_section()
                    if auto_section:
                        self.terminology_section = auto_section
                        app_logger.info(f"Terminology Memory etkinleştirildi. {len(self._terminology_manager.terms)} terim yüklendi.")
                    else:
                        app_logger.info("Terminology Memory: terim yok, prompt bölümü eklenmedi.")
                except Exception as e:
                    app_logger.warning(f"Terminology Manager başlatılamadı: {e}")
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
    def _has_excessive_cjk(text, threshold=0.50):
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

    def _call_api_with_retry(self, full_prompt: str) -> str | None:
        """
        Verilen prompt'u API'ye gönderir, retry + duraklatma/durdurma mantığıyla.
        Başarılı yanıtı string olarak döndürür; hata durumunda None döner.
        """
        retry_count = 0
        while retry_count < self.max_retries:
            while self.is_paused and self.is_running:
                time.sleep(0.5)
            if not self.is_running:
                return None
            # API çağrısından önce hangi endpoint'te olduğumuzu yakala (CAS için)
            with self.data_lock:
                my_ep_idx = self._current_endpoint_idx
            try:
                result = self.provider.generate(full_prompt)
                return result
            except Exception as e:
                last_error = str(e)
                if any(code in last_error for code in ["500", "503"]) and retry_count < self.max_retries - 1:
                    retry_count += 1
                    wait_time = min(2 ** retry_count, 60)
                    self.global_error = f"Sunucu hatası. {wait_time}s sonra tekrar deneniyor. ({retry_count}/{self.max_retries})"
                    sleep_start = time.time()
                    while time.time() - sleep_start < wait_time:
                        if not self.is_running:
                            return None
                        time.sleep(0.5)
                elif ("429" in last_error) or ("ResourceExhausted" in last_error):
                    app_logger.warning(f"429 / ResourceExhausted (EP idx={my_ep_idx}) — sonraki endpoint'e geçiliyor...")
                    if self._try_next_endpoint(my_ep_idx):
                        retry_count = 0
                        continue
                    else:
                        with self.data_lock:
                            self.global_error = "Tüm API endpoint'leri tükendi. Çeviri durduruluyor."
                            self.is_running = False
                        return None
                else:
                    app_logger.warning(f"API çağrısı başarısız: {last_error}")
                    return None
        return None

    def _translate_paragraphs(self, content: str, prompt_hash: str) -> str | None:
        """
        Cache bağımsız standart paragraf bazlı çeviri.

        Cache etkin ise: her paragraf için önce cache kontrol eder, miss olanları API'ye gönderir.
        Cache devre dışı ise: tüm paragrafları doğrudan API'ye gönderir.

        Tek paragraflı dosyalar için None döndürür → tam-dosya akışına geçilir.

        Returns:
            Çevrilmiş ve birleştirilmiş metin veya None.
        """
        from cache.translation_cache import TranslationCache

        paragraphs = TranslationCache.split_into_paragraphs(content)
        if len(paragraphs) <= 1:
            # Tek paragraf — klasik tam-dosya akışına bırak
            return None

        results = {}        # index -> translated_text
        miss_indices = []

        # Cache kontrol (yalnızca cache etkinse)
        if self._cache:
            for idx, para in enumerate(paragraphs):
                cached = self._cache.get_paragraph(para, self.model_version, prompt_hash)
                if cached is not None:
                    if self._has_excessive_cjk(cached):
                        app_logger.warning(f"Paragraf cache hit CJK yüksek, atlanıyor (#{idx})")
                        try:
                            self._cache.remove(para, self.model_version, prompt_hash)
                        except Exception:
                            pass
                        miss_indices.append(idx)
                    else:
                        results[idx] = cached
                        self.paragraph_cache_hit_count += 1
                else:
                    miss_indices.append(idx)
                    self.paragraph_cache_miss_count += 1
        else:
            # Cache yok — hepsi miss
            miss_indices = list(range(len(paragraphs)))

        # Tümü cache hit
        if not miss_indices:
            app_logger.info(f"Tüm paragraflar cache'den alındı ({len(paragraphs)} paragraf)")
            self.cache_hit_count += 1
            return "\n\n".join(results[i] for i in range(len(paragraphs)))

        # Miss paragrafları API'ye gönder
        PARA_SEP = "\n\n===PARAGRAPH_BREAK===\n\n"
        miss_text = PARA_SEP.join(paragraphs[i] for i in miss_indices)

        full_prompt = self.prompt_prefix or ""
        if self.terminology_section:
            full_prompt += "\n\n" + self.terminology_section
        if len(miss_indices) > 1:
            full_prompt += (
                "\n\n[ÖNEMLİ: Metin paragraflar halinde verilmiştir. "
                "Her paragrafı ayrı ayrı çevir. "
                "Paragraflar arasındaki ===PARAGRAPH_BREAK=== ayırıcılarını çıktıda da koru.]\n\n"
            )
        else:
            full_prompt += "\n\n"
        full_prompt += miss_text

        with self.data_lock:
            self.api_request_count += 1
        self.request_made.emit()

        translated_text = self._call_api_with_retry(full_prompt)

        if translated_text is None:
            return None
        if self._has_excessive_cjk(translated_text):
            app_logger.warning("Paragraf bazlı çeviri CJK oranı yüksek.")
            return None

        # Sonuçları paragraflara ayır
        if len(miss_indices) > 1 and "===PARAGRAPH_BREAK===" in translated_text:
            translated_parts = re.split(r'\s*===PARAGRAPH_BREAK===\s*', translated_text)
        else:
            translated_parts = [translated_text]
        translated_parts = [p.strip() for p in translated_parts if p.strip()]

        # Index ile eşleştir
        if len(translated_parts) == len(miss_indices):
            for i, miss_idx in enumerate(miss_indices):
                t = translated_parts[i]
                results[miss_idx] = t
                if self._cache:
                    try:
                        self._cache.set_paragraph(paragraphs[miss_idx], self.model_version, prompt_hash, t)
                    except Exception as e:
                        app_logger.warning(f"Paragraf cache yazma hatası: {e}")
        else:
            app_logger.warning(
                f"Paragraf sayı uyumsuzluğu: beklenen {len(miss_indices)}, alınan {len(translated_parts)}. "
                "Tek parça olarak işleniyor."
            )
            combined = "\n\n".join(translated_parts)
            for i, miss_idx in enumerate(miss_indices):
                results[miss_idx] = combined if i == 0 else ""
            if self._cache:
                combined_orig = "\n\n".join(paragraphs[i] for i in miss_indices)
                try:
                    self._cache.set_paragraph(combined_orig, self.model_version, prompt_hash, combined)
                except Exception as e:
                    app_logger.warning(f"Paragraf cache yazma hatası: {e}")

        if self._cache:
            self.cache_miss_count += 1

        final_parts = [results[i] for i in range(len(paragraphs)) if results.get(i, "")]
        return "\n\n".join(final_parts)

    def _translate_with_paragraph_cache(self, content: str, prompt_hash: str) -> str | None:
        """
        [DEPRECATED] Geriye uyumluluk için korunur.
        Yeni kod _translate_paragraphs() kullanmalıdır.
        """
        return self._translate_paragraphs(content, prompt_hash)


    def _process_single_file(self, i, file_name, prompt_hash, total_files):
        # Duraklatma Döngüsü
        while self.is_paused and self.is_running:
            import time
            time.sleep(0.5)

        if not self.is_running:
            return

        with self.data_lock:
            if self.file_limit is not None and self.translated_count_session >= self.file_limit:
                app_logger.info(f"Belirlenen limit ({self.file_limit}) sayısına ulaşıldı.")
                return

        original_file_path = os.path.join(self.input_folder, file_name)
        translated_file_name = f"translated_{file_name}"
        translated_file_path = os.path.join(self.output_folder, translated_file_name)

        with self.data_lock:
            has_error = file_name in self.translation_errors

        # Zaten çevrilmişse pas geç
        if os.path.exists(translated_file_path) and not has_error:
            self.progress.emit(i + 1, total_files)
            return

        try:
            with open(original_file_path, 'r', encoding='utf-8') as f:
                content_text = f.read()
        except Exception as e:
            with self.data_lock:
                self.translation_errors[file_name] = f"Okuma Hatası: {str(e)}"
            self.progress.emit(i + 1, total_files)
            return

        # ─────────── Paragraf Bazlı Çeviri (Cache bağımsız standart akış) ───────────
        para_result = self._translate_paragraphs(content_text, prompt_hash)
        if para_result is not None:
            if not self._has_excessive_cjk(para_result):
                with open(translated_file_path, 'w', encoding='utf-8') as f:
                    f.write(para_result)
                with self.data_lock:
                    self.translated_count_session += 1
                    if file_name in self.translation_errors:
                        del self.translation_errors[file_name]
                app_logger.info(f"Paragraf bazlı çeviri tamamlandı: {file_name}")
                self.progress.emit(i + 1, total_files)
                return
            else:
                app_logger.warning(f"Paragraf bazlı çeviri CJK kontrolünden geçemedi: {file_name}")

        # ─────────── Klasik Tam Dosya Çeviri Akışı ───────────
        cached_translation = None
        if self._cache:
            cached_translation = self._cache.get_paragraph(content_text, self.model_version, prompt_hash)

        if cached_translation is not None:
            if self._has_excessive_cjk(cached_translation):
                app_logger.warning(f"Cache hit ancak CJK oranı yüksek, cache atlanıyor: {file_name}")
                try:
                    with self.data_lock:
                        self._cache.remove(content_text, self.model_version, prompt_hash)
                except Exception:
                    pass
            else:
                with self.data_lock:
                    self.cache_hit_count += 1
                app_logger.info(f"Cache hit: {file_name}")
                with open(translated_file_path, 'w', encoding='utf-8') as f:
                    f.write(cached_translation)
                with self.data_lock:
                    self.translated_count_session += 1
                    if file_name in self.translation_errors:
                        del self.translation_errors[file_name]
                self.progress.emit(i + 1, total_files)
                return

        if self._cache:
            with self.data_lock:
                self.cache_miss_count += 1
        if self.prompt_prefix:
            full_prompt = self.prompt_prefix
        else:
            full_prompt = ""
        if self.terminology_section:
            full_prompt += "\n\n" + self.terminology_section
        full_prompt += "\n\n" + content_text

        translated_text = None
        last_error = ""
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

            # API çağrısından önce hangi endpoint'te olduğumuzu yakala (CAS için)
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
                if any(code in last_error for code in ["500", "503"]) and retry_count < self.max_retries - 1:
                    retry_count += 1
                    wait_time = min(2 ** retry_count, 60)
                    self.global_error = f"Sunucu hatası ({last_error}). {wait_time} saniye sonra tekrar denenecek. Deneme Sayısı: {retry_count}/{self.max_retries}"
                    import time
                    sleep_start = time.time()
                    while time.time() - sleep_start < wait_time:
                        if not self.is_running:
                            break
                        time.sleep(0.5)
                elif ("429" in last_error) or ("ResourceExhausted" in last_error):
                    app_logger.warning(f"429 / ResourceExhausted [{file_name}] (EP idx={my_ep_idx}) — sonraki endpoint'e geçiliyor...")
                    if self._try_next_endpoint(my_ep_idx):
                        retry_count = 0
                        continue
                    else:
                        with self.data_lock:
                            self.global_error = "Tüm API endpoint'leri tükendi. Çeviri durduruluyor."
                            self.is_running = False
                        api_limit_hit = True
                        with self.data_lock:
                            self.translation_errors[file_name] = f"Kota Aşıldı: {last_error}"
                        try:
                            with open(translated_file_path, 'w', encoding='utf-8') as f:
                                f.write(f"Çeviri hatası (Kota aşıldı): {last_error}\n\nOrijinal Metin:\n{content_text[:500]}...")
                        except:
                            pass
                        break
                else:
                    with self.data_lock:
                        self.translation_errors[file_name] = f"Çeviri Hatası: {last_error}"
                    try:
                        with open(translated_file_path, 'w', encoding='utf-8') as f:
                            f.write(f"Çeviri hatası: {last_error}\n\nOrijinal Metin:\n{content_text[:500]}...")
                    except:
                        pass
                    break

        if not self.is_running:
            return

        if translated_text is not None:
            if self._has_excessive_cjk(translated_text):
                app_logger.warning(f"Çeviri sonucu CJK yüksek: {file_name}")
                with self.data_lock:
                    self.translation_errors[file_name] = "Çeviri Hatası: Çince/Korece karakter oranı çok yüksek (çevrilmemiş içerik)"
            else:
                with open(translated_file_path, 'w', encoding='utf-8') as f:
                    f.write(translated_text)
                with self.data_lock:
                    self.translated_count_session += 1

                if self._cache:
                    try:
                        with self.data_lock:
                            self._cache.set_paragraph(content_text, self.model_version, prompt_hash, translated_text)
                    except Exception as e:
                        app_logger.warning(f"Cache yazma hatası: {e}")

        self.progress.emit(i + 1, total_files)

    # ═══════════════════════════════════════════════════════
    # BATCH ÇEVİRİ — Yeni metotlar
    # ═══════════════════════════════════════════════════════

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

            # Yeni batch mi başlatılmalı?
            if current_batch and (
                current_chars + file_size > self.max_batch_chars
                or len(current_batch) >= self.max_chapters_per_batch
            ):
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
            content = contents.get(file_name, "")
            parts.append(
                f"===CHAPTER_START===\n{content.strip()}\n===CHAPTER_END==="
            )
        return "\n\n".join(parts)

    def parse_batch_response(self, response: str, batch: list[str],
                             contents: dict[str, str], prompt_hash: str) -> dict[str, str]:
        """
        API yanıtını ===CHAPTER_START=== / ===CHAPTER_END=== ayraçlarıyla parse eder.
        Bölümler index sırasıyla batch listesine eşleştirilir.
        Parse edilen her bölüm paragraf bazlı cache'e yazılır.

        Returns: {dosya_adı: çevrilmiş_içerik} — sadece başarıyla parse edilenler.
        """
        pattern = re.compile(
            r'===CHAPTER_START===(.*?)===CHAPTER_END===',
            re.DOTALL
        )
        parsed_blocks = pattern.findall(response)
        result = {}

        for i, file_name in enumerate(batch):
            if i >= len(parsed_blocks):
                break
            chapter_text = parsed_blocks[i].strip()
            if not chapter_text:
                continue
            if self._has_excessive_cjk(chapter_text):
                app_logger.warning(f"Batch parse: CJK oranı yüksek, atlanıyor — {file_name}")
                continue
            result[file_name] = chapter_text

            # Parse edilen bölümü paragraf bazlı cache'e yaz
            if self._cache and file_name in contents:
                original = contents[file_name]
                from cache.translation_cache import TranslationCache
                paragraphs = TranslationCache.split_into_paragraphs(original)
                translated_paragraphs = TranslationCache.split_into_paragraphs(chapter_text)
                if len(paragraphs) == len(translated_paragraphs):
                    for orig_para, trans_para in zip(paragraphs, translated_paragraphs):
                        try:
                            self._cache.set_paragraph(orig_para, self.model_version, prompt_hash, trans_para)
                        except Exception as e:
                            app_logger.warning(f"Batch cache yazma hatası: {e}")
                else:
                    # Sayı uyuşmazsa tüm içeriği tek girdi olarak cache'e yaz
                    try:
                        self._cache.set_paragraph(original, self.model_version, prompt_hash, chapter_text)
                    except Exception as e:
                        app_logger.warning(f"Batch cache tek-parça yazma hatası: {e}")

        app_logger.info(f"Batch parse: {len(result)}/{len(batch)} bölüm parse edildi.")
        return result

    def _process_batch(self, batch: list[str], batch_idx: int,
                       total_batches: int, prompt_hash: str) -> list[str]:
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
        # Duraklatma / durdurma
        while self.is_paused and self.is_running:
            time.sleep(0.5)
        if not self.is_running:
            return batch

        app_logger.info(f"Batch {batch_idx + 1}/{total_batches}: {len(batch)} dosya işleniyor — {batch}")

        # İçerikleri oku
        contents = {}
        unreadable = []
        for file_name in batch:
            file_path = os.path.join(self.input_folder, file_name)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    contents[file_name] = f.read()
            except Exception as e:
                app_logger.error(f"Batch okuma hatası [{file_name}]: {e}")
                with self.data_lock:
                    self.translation_errors[file_name] = f"Okuma Hatası: {e}"
                unreadable.append(file_name)

        readable_batch = [f for f in batch if f not in unreadable]
        if not readable_batch:
            return []

        # Batch prompt oluştur
        batch_input = self.format_batch_input(readable_batch, contents)
        full_prompt = self.prompt_prefix or ""
        if self.terminology_section:
            full_prompt += "\n\n" + self.terminology_section
        full_prompt += (
            "\n\n[ÖNEMLİ: Aşağıda birden fazla bölüm verilmiştir. "
            "Her bölümü ===CHAPTER_START=== ile başlayan ve ===CHAPTER_END=== ile biten "
            "bloklar halinde ayrı ayrı çevir. Ayraçları ve sıralamayı kesinlikle koru.]\n\n"
        )
        full_prompt += batch_input

        with self.data_lock:
            self.api_request_count += 1
        self.request_made.emit()

        response = self._call_api_with_retry(full_prompt)

        if response is None:
            app_logger.warning(f"Batch {batch_idx + 1}: API yanıtı alınamadı.")
            return readable_batch

        # Parse
        parsed = self.parse_batch_response(response, readable_batch, contents, prompt_hash)

        failed = []
        if len(parsed) == 0:
            # Hiç parse edilemedi → batch'i böl ve tekrar dene
            app_logger.warning(f"Batch {batch_idx + 1}: Parse başarısız. Batch bölünüyor...")
            return self._fallback_split_batch(readable_batch, batch_idx, total_batches, prompt_hash)

        # Başarılı olanları kaydet
        for file_name, chapter_text in parsed.items():
            translated_file_path = os.path.join(self.output_folder, f"translated_{file_name}")
            try:
                with open(translated_file_path, 'w', encoding='utf-8') as f:
                    f.write(chapter_text)
                with self.data_lock:
                    self.translated_count_session += 1
                    if file_name in self.translation_errors:
                        del self.translation_errors[file_name]
                app_logger.info(f"Batch çeviri kaydedildi: {file_name}")
            except Exception as e:
                app_logger.error(f"Batch kaydetme hatası [{file_name}]: {e}")
                failed.append(file_name)

        # Parse edilemeyen dosyalar fallback'e
        for file_name in readable_batch:
            if file_name not in parsed:
                failed.append(file_name)

        return failed

    def _fallback_split_batch(self, batch: list[str], batch_idx: int,
                              total_batches: int, prompt_hash: str) -> list[str]:
        """
        Parse başarısız olan batch'i ikiye bölerek tekrar dener.
        İkiye bölme de başarısız olursa dosyaları fallback listesine ekler.
        """
        if len(batch) <= 1:
            # Tek dosya — _process_single_file fallback'i üst katman halleder
            return batch

        mid = len(batch) // 2
        first_half = batch[:mid]
        second_half = batch[mid:]
        app_logger.info(f"Batch bölünüyor: {first_half} | {second_half}")

        failed = []
        for half in [first_half, second_half]:
            if len(half) == 1:
                # Tek dosyayı doğrudan _process_single_file ile işle
                self._process_single_file(0, half[0], prompt_hash, 1)
            else:
                sub_failed = self._process_batch(half, batch_idx, total_batches, prompt_hash)
                failed.extend(sub_failed)
        return failed

    def _run_batch_mode(self, files_to_translate: list[str],
                        total_files: int, prompt_hash: str):
        """
        Batch modunda tüm çeviri döngüsünü yürütür.
        Başarısız kalan dosyalar _process_single_file() ile tek tek işlenir.
        """
        app_logger.info(
            f"Batch Çeviri başlatılıyor. Toplam: {total_files} dosya, "
            f"maxBatchChars={self.max_batch_chars}, maxChaptersPerBatch={self.max_chapters_per_batch}"
        )

        # Zaten çevrilmiş dosyaları atla
        pending = []
        for file_name in files_to_translate:
            translated_path = os.path.join(self.output_folder, f"translated_{file_name}")
            with self.data_lock:
                has_error = file_name in self.translation_errors
            if os.path.exists(translated_path) and not has_error:
                self.progress.emit(files_to_translate.index(file_name) + 1, total_files)
            else:
                pending.append(file_name)

        batches = self.build_batches(pending)
        app_logger.info(f"Batch Çeviri: {len(pending)} dosya, {len(batches)} batch oluşturuldu.")

        _progress_counter = [total_files - len(pending)]  # thread-safe ilerleme sayacı (listeyle mutable closure)

        def _run_single_batch(args):
            """Tek bir batch'i işler: API çağrısı + fallback. Async executor ile uyumlu."""
            batch_idx, batch = args
            if not self.is_running:
                return
            failed = self._process_batch(batch, batch_idx, len(batches), prompt_hash)
            with self.data_lock:
                _progress_counter[0] += len(batch)
                cur_progress = _progress_counter[0]
            self.progress.emit(cur_progress, total_files)
            # Başarısız dosyaları tek tek dene
            for file_name in failed:
                if not self.is_running:
                    break
                app_logger.info(f"Batch fallback → tekli çeviri: {file_name}")
                idx = files_to_translate.index(file_name) if file_name in files_to_translate else 0
                self._process_single_file(idx, file_name, prompt_hash, total_files)

        if self.async_enabled and len(batches) > 1:
            # ── Batch + Async: Batch'ler ThreadPoolExecutor ile paralel işlenir ──
            import concurrent.futures
            app_logger.info(
                f"Batch Async Modu: {self.async_threads} thread ile "
                f"{len(batches)} batch paralel işleniyor."
            )
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.async_threads) as executor:
                future_to_idx = {
                    executor.submit(_run_single_batch, (batch_idx, batch)): batch_idx
                    for batch_idx, batch in enumerate(batches)
                    if self.is_running
                }
                for fut in concurrent.futures.as_completed(future_to_idx):
                    b_idx = future_to_idx[fut]
                    try:
                        fut.result()
                    except Exception as be:
                        app_logger.error(f"Batch async hatası [batch {b_idx}]: {be}")
                    if not self.is_running:
                        break
        else:
            # ── Sıralı Batch: async kapalı veya tek batch ──
            if self.async_enabled:
                app_logger.info("Batch Async Modu: Yalnızca 1 batch var, sıralı işleniyor.")
            for batch_idx, batch in enumerate(batches):
                if not self.is_running:
                    break
                _run_single_batch((batch_idx, batch))

        app_logger.info("Batch Çeviri tamamlandı.")

    def run(self):
        if not self.provider:
            self.error.emit("LLM sağlayıcı yapılandırılmamış. API anahtarı veya endpoint ayarlarını kontrol edin.")
            self.finished.emit(self.shutdown_on_finish)
            return

        self.translation_start_time = time.time()

        # Cache ve Terminology başlat
        self._init_cache_and_terminology()

        # Prompt hash (cache key + batch mod için — her zaman hesaplanır)
        from cache.translation_cache import TranslationCache
        prompt_hash = TranslationCache.hash_prompt(self.prompt_prefix or "")

        # Hata logunu yükle
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
                # ─── Batch Modu ───
                self._run_batch_mode(files_to_translate, total_files, prompt_hash)
            elif self.async_enabled:
                import concurrent.futures
                app_logger.info(f"Asenkron Çeviri: {self.async_threads} thread ile başlatılıyor. Toplam dosya: {total_files}")
                
                executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.async_threads)
                futures = {}
                
                try:
                    for i, file_name in enumerate(files_to_translate):
                        if not self.is_running:
                            app_logger.warning(f"Async: is_running=False — görev gönderimi durduruldu ({i}/{total_files})")
                            break
                        fut = executor.submit(self._process_single_file, i, file_name, prompt_hash, total_files)
                        futures[fut] = file_name
                    
                    app_logger.info(f"Async: {len(futures)} görev gönderildi, tamamlanmaları bekleniyor...")
                    
                    for fut in concurrent.futures.as_completed(futures):
                        fname = futures[fut]
                        try:
                            fut.result()
                            app_logger.debug(f"Async: Görev tamamlandı — {fname}")
                        except Exception as thread_e:
                            app_logger.error(f"Async Thread İstisnası [{fname}]: {type(thread_e).__name__}: {thread_e}")
                        
                        if not self.is_running:
                            app_logger.warning("Async: is_running=False — kalan görevler beklenecek, yeni görev gönderilmeyecek")
                            break
                finally:
                    # Executor'ı KAPATARAK tüm thread'lerin bitmesini bekle
                    # Bu satır QThread Destroyed hatasının esas çözümüdür
                    app_logger.info("Async: Executor kapatılıyor (tüm thread'ler bekleniyor)...")
                    executor.shutdown(wait=True, cancel_futures=False)
                    app_logger.info("Async: Executor tamamen kapandı.")
            else:
                # Klasik Sıralı (Sequential) işlem
                app_logger.info("Klasik (Ardışık) Çeviri başlatılıyor.")
                for i, file_name in enumerate(files_to_translate):
                    if not self.is_running:
                        app_logger.info(f"Sıralı çeviri durduruldu: {i}/{total_files}")
                        break
                    self._process_single_file(i, file_name, prompt_hash, total_files)
                    
        except Exception as e:
            import traceback
            app_logger.critical(f"TranslationWorker Kritik Hata: {type(e).__name__}: {e}\n{traceback.format_exc()}")
            try:
                self.error.emit(f"Genel hata: {type(e).__name__}: {e}")
            except RuntimeError:
                pass
        finally:
            app_logger.info(f"TranslationWorker: finally bloğu — global_error={'var' if self.global_error else 'yok'}, is_running={self.is_running}")
            
            if self.global_error:
                try:
                    app_logger.error(f"TranslationWorker: Global hata sinyali gönderiliyor — {self.global_error}")
                    self.error.emit(self.global_error)
                except RuntimeError as e:
                    app_logger.error(f"TranslationWorker: error.emit sonrası RuntimeError (bekleniyor): {e}")
                
            # Cache istatistikleri logla
            if self._cache:
                elapsed = time.time() - self.translation_start_time if self.translation_start_time else 0
                app_logger.info(
                    f"Cache istatistikleri — "
                    f"Dosya Hit: {self.cache_hit_count}, Dosya Miss: {self.cache_miss_count}, "
                    f"Paragraf Hit: {self.paragraph_cache_hit_count}, "
                    f"Paragraf Miss: {self.paragraph_cache_miss_count}, "
                    f"API çağrısı: {self.api_request_count}, "
                    f"Süre: {elapsed:.1f}s"
                )

            try:
                with open(self.error_log_path, 'w', encoding='utf-8') as f:
                    json.dump(self.translation_errors, f, indent=4, ensure_ascii=False)
            except:
                pass
            
            app_logger.info("TranslationWorker: finished sinyali gönderiliyor...")
            try:
                self.finished.emit(self.shutdown_on_finish)
            except RuntimeError as e:
                app_logger.error(f"TranslationWorker: finished.emit sonrası RuntimeError: {e}")