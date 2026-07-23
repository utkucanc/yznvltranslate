# Proje Dosya Sistemi

Bu belge, **yznvltranslate-main** projesindeki dizin yapısı ve temel dosyalar hakkında genel bir bakış sağlar.

## Dizin Ağacı
```text
yznvltranslate-main/
├── AppConfigs/         # Uygulama yapılandırması ve günlükler
├── cache/             # Çeviri önbellek yönetimi
├── core/              # Çekirdek iş mantığı
│   └── workers/       # Çeviri görevleri için asenkron işçiler
├── terminology/       # Terminoloji yönetimi
├── ui/                # Kullanıcı arayüzü bileşenleri ve diyaloglar
├── main_window.py     # Ana Giriş Noktası
├── dialogs.py         # Genel diyaloglar
├── logger.py          # Günlük tutma yapılandırması
├── 69shuba.js         # Kazıyıcı Mantığı
├── booktoki.js        # Kazıyıcı Mantığı
├── novelfire.js       # Kazıyıcı Mantığı
├── requirements.txt   # Bağımlılıklar
├── setup.py           # Kurulum betiği
└── file-tree.md       # Proje dizin yapısı ve temel dosyalar hakkında açıklama
```

## Kök Dizin
- `69shuba.js`: 69shuba için kazıyıcı betiği.
- `booktoki.js`: Booktoki için kazıyıcı betiği.
- `dialogs.py`: Genel diyalog uygulamaları.
- `logger.py`: Günlük tutma yapılandırması ve yardımcı araçlar.
- `main_window.py`: Ana uygulama penceresi ve giriş noktası.
- `novelfire.js`: Novelfire için kazıyıcı betiği.
- `requirements.txt`: Proje bağımlılıkları.
- `setup.py`: Kurulum ve paketleme betiği.

## Çekirdek Modülü (`/core`)
- `__init__.py`: Paket başlatıcısı.
- `ch-kontrol.py`: Bölüm kontrol yardımcı araçları.
- `chapter_check_worker.py`: Bölüm tutarlılığını kontrol eden işçi.
- `database_manager.py`: SQLite veritabanı işlemleri.
- `download_controller.py`: İndirmeleri yönetme mantığı.
- `file_list_manager.py`: Giriş/çıkış dosyalarının yönetimi.
- `js_create.py`: JavaScript kazıyıcı dosyaları oluşturmak için yardımcı araç.
- `kr-kontrol.py`: Korece metin kontrol/doğrulama aracı.
- `llm_provider.py`: LLM API'leri (Gemini vb.) için arayüz.
- `merge_controller.py`: Çevrilmiş segmentleri birleştirme mantığı.
- `process_controller.py`: Çeviri için ana düzenleme mantığı.
- `project_manager.py`: Proje yaşam döngüsü yönetimi.
- `temizlik.py`: Metin temizleme ve biçimlendirme aracı.
- `token_controller.py`: Token sayma ve yönetim mantığı.
- `translation_controller.py`: Çekirdek çeviri iş akışı mantığı.
- `ui_state_manager.py`: İş parçacığı güvenli (thread-safe) kullanıcı arayüzü güncellemeleri.
- `utils.py`: Genel yardımcı fonksiyonlar.

### İşçiler (`/core/workers`)
- `cleaning_worker.py`: Metin temizleme için asenkron işçi.
- `download_worker.py`: Web kazıma/indirme için asenkron işçi.
- `epub_worker.py`: EPUB oluşturma ve işleme.
- `merging_worker.py`: Dosyaları birleştirmek için asenkron işçi.
- `ml_terminology_extractor.py`: LLM ile otomatik terminoloji çıkarma.
- `ml_terminology_worker.py`: Terminoloji görevleri için işçi.
- `prompt_generator.py`: LLM istemlerini (prompts) oluşturma mantığı.
- `split_worker.py`: Büyük dosyaları bölme mantığı.
- `token_count_worker.py`: Token tahmini için asenkron işçi.
- `token_counter.py`: Token sayma uygulaması.
- `translation_error_check_worker.py`: Çeviri sonrası hata tespiti.
- `translation_quality_checker.py`: Metin benzerliği (%80+), langdetect ve CJK ile çok katmanlı kalite kontrolü.
- `translation_worker.py`: LLM çağrılarını yürüten ana işçi.

## UI Bileşenleri (`/ui`)
- `__init__.py`: Paket başlatıcısı.
- `api_key_editor_dialog.py`: Servis anahtarlarını düzenleme diyaloğu.
- `api_stats_dialog.py`: API kullanımını görüntüleme diyaloğu.
- `app_settings_dialog.py`: Genel uygulama ayarları.
- `file_preview_dialog.py`: Metin dosyalarını önizleme.
- `file_table_interactions.py`: Tablo olaylarını işleme.
- `file_table_manager.py`: Dosya listesi tablosunu yönetme.
- `gemini_version_dialog.py`: Gemini model seçimi.
- `mcp_server_dialog.py`: MCP sunucu yapılandırması.
- `menu_bar_builder.py`: Ana menü oluşturma.
- `new_project_dialog.py`: Yeni proje başlatma sihirbazı.
- `post_download_dialog.py`: İndirme bittikten sonraki seçenekler.
- `project_settings_dialog.py`: Bireysel proje yapılandırmaları.
- `prompt_editor_dialog.py`: LLM istem şablonlarını düzenleme.
- `request_counter_manager.py`: API isteklerini takip etme.
- `right_panel_builder.py`: Ana kontrol paneli arayüzünü oluşturma.
- `selenium_menu_dialog.py`: Selenium'a özel indirme seçenekleri.
- `split_dialogs.py`: Dosya bölme diyalogları.
- `status_bar_manager.py`: Alt durum çubuğu güncellemeleri.
- `terminology_dialog.py`: Terminoloji veritabanlarını yönetme.
- `text_editor_dialog.py`: Dahili metin düzenleme yeteneği.

## Terminoloji Yönetimi (`/terminology`)
- `__init__.py`: Paket başlatıcısı.
- `terminology_manager.py`: Terminoloji için CRUD (Oluşturma, Okuma, Güncelleme, Silme) işlemleri.

## Çeviri Önbelleği (`/cache`)
- `__init__.py`: Paket başlatıcısı.
- `translation_cache.py`: Çevirilerin kalıcı olarak önbelleğe alınması.

## Uygulama Yapılandırması (`/AppConfigs`)
- `APIKeys/`: API anahtarlarını depolama dizini (git tarafından dikkate alınmaz).
- `GVersion.ini`: Gemini model sürümlerini takip eder.
- `MCP_Endpoints.json`: Yapılandırılmış MCP uç noktaları.
- `Promts/`: İstem şablonları dizini.
- `app.log`: Uygulama çalışma zamanı günlükleri.
- `app_settings.json`: Genel kullanıcı tercihleri.
- `request_count.json`: Kalıcı istek sayacı.
- `request_stats.json`: Detaylı API kullanım istatistikleri.
- `themes/`: UI temaları ve stillendirme.
