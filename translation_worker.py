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
                 project_path=None, cache_enabled=True, terminology_enabled=True):
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

        # Cache & Terminology nesneleri (run() içinde başlatılır)
        self._cache = None
        self._terminology_manager = None

    def _init_provider(self):
        """LLMProvider'ı başlatır. Geriye uyumlu: endpoint yoksa doğrudan API key ile çalışır."""
        try:
            from llm_provider import LLMProvider
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

    def _translate_with_paragraph_cache(self, content: str, prompt_hash: str) -> str | None:
        """
        Paragraf bazlı cache ile çeviri yapar.
        
        1. Dosya içeriğini paragraflara böler
        2. Her paragraf için cache kontrol eder
        3. Cache miss olan paragrafları batch olarak LLM'e gönderir
        4. Sonuçları birleştirir ve döndürür
        
        Returns:
            Çevrilmiş metin veya None (hata durumunda)
        """
        from cache.translation_cache import TranslationCache

        paragraphs = TranslationCache.split_into_paragraphs(content)

        if len(paragraphs) <= 1:
            # Tek paragraf — doğrudan döndür, normal akışta işlenecek
            return None

        # Her paragraf için cache kontrol
        results = {}  # index -> translated_text
        miss_indices = []

        for idx, para in enumerate(paragraphs):
            cached = self._cache.get_paragraph(para, self.model_version, prompt_hash)
            if cached is not None:
                # CJK kontrolü
                if self._has_excessive_cjk(cached):
                    app_logger.warning(f"Paragraf cache hit ancak CJK oranı yüksek, atlanıyor (paragraf #{idx})")
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

        # Tümü cache hit ise birleştir ve döndür
        if not miss_indices:
            app_logger.info(f"Tüm paragraflar cache'den alındı ({len(paragraphs)} paragraf)")
            self.cache_hit_count += 1
            return "\n\n".join(results[i] for i in range(len(paragraphs)))

        # Cache miss varsa — LLM'e gönder
        # Cache miss olanları tek metin olarak birleştir
        # Paragraf ayırıcı olarak özel marker kullan
        PARA_SEP = "\n\n===PARAGRAPH_BREAK===\n\n"
        miss_text = PARA_SEP.join(paragraphs[i] for i in miss_indices)

        # Prompt oluştur
        full_prompt = self.prompt_prefix or ""
        if self.terminology_section:
            full_prompt += "\n\n" + self.terminology_section
        
        # Paragraf ayırma talimatı ekle
        if len(miss_indices) > 1:
            full_prompt += (
                "\n\n[ÖNEMLİ: Metin paragraflar halinde verilmiştir. "
                "Her paragrafı ayrı ayrı çevir. "
                "Paragraflar arasındaki ===PARAGRAPH_BREAK=== ayırıcılarını çıktıda da koru.]\n\n"
            )
        else:
            full_prompt += "\n\n"

        full_prompt += miss_text

        # API çağrısı
        translated_text = None
        last_error = ""
        retry_count = 0

        self.api_request_count += 1
        self.request_made.emit()

        while retry_count < self.max_retries:
            while self.is_paused and self.is_running:
                time.sleep(0.5)

            if not self.is_running:
                return None

            try:
                translated_text = self.provider.generate(full_prompt)
                break
            except Exception as e:
                last_error = str(e)
                if ("500" in last_error) and retry_count < self.max_retries - 1:
                    retry_count += 1
                    wait_time = 2 ** retry_count
                    sleep_start = time.time()
                    while time.time() - sleep_start < wait_time:
                        if not self.is_running:
                            return None
                        time.sleep(0.5)
                elif ("429" in last_error) or ("ResourceExhausted" in last_error):
                    self.error.emit("API sınırına ulaşıldı. Lütfen bekleyin veya API kullanımınızı kontrol edin.")
                    return None
                else:
                    return None

        if translated_text is None:
            return None

        # CJK kontrolü (genel)
        if self._has_excessive_cjk(translated_text):
            app_logger.warning("Paragraf bazlı çeviri sonucu CJK oranı yüksek.")
            return None

        # Çeviri sonucunu paragraflara ayır
        if len(miss_indices) > 1 and PARA_SEP.strip() in translated_text:
            translated_parts = translated_text.split(PARA_SEP.strip())
        elif len(miss_indices) > 1 and "===PARAGRAPH_BREAK===" in translated_text:
            translated_parts = translated_text.split("===PARAGRAPH_BREAK===")
        else:
            translated_parts = [translated_text]

        # Temizle
        translated_parts = [p.strip() for p in translated_parts if p.strip()]

        # Eşleştirme: miss_indices ile translated_parts
        if len(translated_parts) == len(miss_indices):
            # Birebir eşleşme — her birini cache'e yaz
            for i, miss_idx in enumerate(miss_indices):
                t = translated_parts[i]
                results[miss_idx] = t
                try:
                    self._cache.set_paragraph(
                        paragraphs[miss_idx], self.model_version, prompt_hash, t
                    )
                except Exception as e:
                    app_logger.warning(f"Paragraf cache yazma hatası: {e}")
        else:
            # Paragraf sayısı uyuşmuyor — tüm çeviriyi tek parça olarak kullan
            app_logger.warning(
                f"Paragraf sayı uyumsuzluğu: beklenen {len(miss_indices)}, "
                f"alınan {len(translated_parts)}. Tek parça olarak işleniyor."
            )
            # Tüm miss paragraflarını tek bir çeviri olarak birleştirip ilk miss'e koy
            combined = "\n\n".join(translated_parts)
            # Tüm miss indekslerini sonuçtan çıkar, birleşik çeviriyi kullan
            for i, miss_idx in enumerate(miss_indices):
                if i == 0:
                    results[miss_idx] = combined
                else:
                    results[miss_idx] = ""  # Sonraki miss'ler boş

            # Cache'e tek parça olarak yaz (tüm miss metnini birleştir)
            combined_original = "\n\n".join(paragraphs[i] for i in miss_indices)
            try:
                self._cache.set_paragraph(
                    combined_original, self.model_version, prompt_hash, combined
                )
            except Exception as e:
                app_logger.warning(f"Paragraf cache yazma hatası: {e}")

        self.cache_miss_count += 1

        # Sonuçları birleştir (boş olanları atla)
        final_parts = []
        for i in range(len(paragraphs)):
            text = results.get(i, "")
            if text:
                final_parts.append(text)
        
        return "\n\n".join(final_parts)

    def run(self):
        if not self.provider:
            self.error.emit("LLM sağlayıcı yapılandırılmamış. API anahtarı veya endpoint ayarlarını kontrol edin.")
            self.finished.emit(self.shutdown_on_finish)
            return

        self.translation_start_time = time.time()

        # Cache ve Terminology başlat
        self._init_cache_and_terminology()

        # Prompt hash (cache key için)
        prompt_hash = ""
        if self._cache:
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

            translated_count_session = 0

            for i, file_name in enumerate(files_to_translate):
                # Duraklatma Döngüsü
                while self.is_paused and self.is_running:
                    time.sleep(0.5)

                if not self.is_running:
                    break

                # Limit Kontrolü
                if self.file_limit is not None and translated_count_session >= self.file_limit:
                    app_logger.info(f"Belirlenen limit ({self.file_limit}) sayısına ulaşıldı.")
                    break

                original_file_path = os.path.join(self.input_folder, file_name)
                translated_file_name = f"translated_{file_name}"
                translated_file_path = os.path.join(self.output_folder, translated_file_name)

                # Zaten çevrilmişse pas geç
                if os.path.exists(translated_file_path) and file_name not in self.translation_errors:
                    self.progress.emit(i + 1, total_files)
                    continue

                try:
                    with open(original_file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except Exception as e:
                    self.translation_errors[file_name] = f"Okuma Hatası: {str(e)}"
                    self.progress.emit(i + 1, total_files)
                    continue

                # ─────────── Paragraf Bazlı Cache Denemesi ───────────
                if self._cache:
                    para_result = self._translate_with_paragraph_cache(content, prompt_hash)
                    if para_result is not None:
                        # Paragraf bazlı cache başarılı (tamamen veya kısmen cache + API)
                        if not self._has_excessive_cjk(para_result):
                            with open(translated_file_path, 'w', encoding='utf-8') as f:
                                f.write(para_result)
                            translated_count_session += 1

                            if file_name in self.translation_errors:
                                del self.translation_errors[file_name]

                            app_logger.info(f"Paragraf bazlı çeviri tamamlandı: {file_name}")
                            self.progress.emit(i + 1, total_files)
                            continue
                        else:
                            app_logger.warning(f"Paragraf bazlı çeviri CJK kontrolünden geçemedi: {file_name}")

                # ─────────── Klasik Tam Dosya Çeviri Akışı ───────────
                # (Tek paragraf veya paragraf cache başarısızsa)

                # Dosya bazlı cache kontrolü
                cached_translation = None
                if self._cache:
                    cached_translation = self._cache.get_paragraph(content, self.model_version, prompt_hash)

                if cached_translation is not None:
                    if self._has_excessive_cjk(cached_translation):
                        app_logger.warning(f"Cache hit ancak CJK oranı yüksek, cache atlanıyor: {file_name}")
                        try:
                            self._cache.remove(content, self.model_version, prompt_hash)
                        except Exception:
                            pass
                    else:
                        self.cache_hit_count += 1
                        app_logger.info(f"Cache hit: {file_name}")
                        with open(translated_file_path, 'w', encoding='utf-8') as f:
                            f.write(cached_translation)
                        translated_count_session += 1

                        if file_name in self.translation_errors:
                            del self.translation_errors[file_name]

                        self.progress.emit(i + 1, total_files)
                        continue

                # Cache miss — API çağrısı gerekiyor
                if self._cache:
                    self.cache_miss_count += 1

                # Prompt oluşturma (terminology varsa ekle)
                full_prompt = self.prompt_prefix or ""
                if self.terminology_section:
                    full_prompt += "\n\n" + self.terminology_section
                full_prompt += "\n\n" + content

                translated_text = None
                last_error = ""
                api_limit_hit = False
                retry_count = 0

                self.api_request_count += 1
                self.request_made.emit()
                while retry_count < self.max_retries:
                    while self.is_paused and self.is_running:
                        time.sleep(0.5)

                    if not self.is_running:
                        break

                    try:
                        translated_text = self.provider.generate(full_prompt)

                        if file_name in self.translation_errors:
                            del self.translation_errors[file_name]
                        break

                    except Exception as e:
                        last_error = str(e)
                        if ("500" in last_error) and retry_count < self.max_retries - 1:
                            retry_count += 1
                            wait_time = 2 ** retry_count
                            sleep_start = time.time()
                            while time.time() - sleep_start < wait_time:
                                if not self.is_running:
                                    break
                                time.sleep(0.5)
                        elif ("429" in last_error) or ("ResourceExhausted" in last_error):
                            self.error.emit("API sınırına ulaşıldı. Lütfen bekleyin veya API kullanımınızı kontrol edin.")
                            api_limit_hit = True

                            self.translation_errors[file_name] = f"Kota Aşıldı: {last_error}"
                            try:
                                with open(translated_file_path, 'w', encoding='utf-8') as f:
                                    f.write(f"Çeviri hatası (Kota aşıldı): {last_error}\n\nOrijinal Metin:\n{content[:500]}...")
                            except:
                                pass
                            break
                        else:
                            self.translation_errors[file_name] = f"Çeviri Hatası: {last_error}"
                            try:
                                with open(translated_file_path, 'w', encoding='utf-8') as f:
                                    f.write(f"Çeviri hatası: {last_error}\n\nOrijinal Metin:\n{content[:500]}...")
                            except:
                                pass
                            break

                if api_limit_hit:
                    break

                if not self.is_running:
                    break

                if translated_text is not None:
                    # --- CJK Karakter Kontrolü ---
                    if self._has_excessive_cjk(translated_text):
                        app_logger.warning(f"Çeviri sonucu Çince/Korece karakter oranı çok yüksek (>50%), dosya kaydedilmedi: {file_name}")
                        self.translation_errors[file_name] = "Çeviri Hatası: Çince/Korece karakter oranı çok yüksek (çevrilmemiş içerik)"
                    else:
                        with open(translated_file_path, 'w', encoding='utf-8') as f:
                            f.write(translated_text)
                        translated_count_session += 1

                        # --- Cache'e kaydet ---
                        if self._cache:
                            try:
                                self._cache.set_paragraph(content, self.model_version, prompt_hash, translated_text)
                            except Exception as e:
                                app_logger.warning(f"Cache yazma hatası: {e}")

                self.progress.emit(i + 1, total_files)

        except Exception as e:
            self.error.emit(f"Genel hata: {str(e)}")
        finally:
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
            self.finished.emit(self.shutdown_on_finish)