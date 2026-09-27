# Proje Dosya Sistemi

Bu belge, **yznvltranslate-main** projesindeki dizin yapısı ve temel dosyalar hakkında genel bir bakış sağlar.

## Dizin Ağacı
```text
Directory structure:
└── yznvltranslate/
    ├── README.md
    ├── CeviriUygulamasi.spec
    ├── dialogs.py
    ├── file-tree.md
    ├── LICENSE
    ├── logger.py
    ├── main_window.spec
    ├── README-EN.md
    ├── requirements.txt
    ├── setup.py
    ├── start.bat
    ├── AppConfigs/
    │   ├── app_settings.json
    │   ├── GVersion.ini
    │   ├── MCP_Endpoints.json
    │   ├── APIKeys/
    │   │   ├── APIKey1.txt
    │   │   ├── token1.txt
    │   │   ├── token2.txt
    │   │   └── MCP/
    │   │       ├── default_gemini.txt
    │   │       └── localllm.txt
    │   ├── locales/
    │   │   ├── en.json
    │   │   ├── logger.json
    │   │   ├── logger_en.json
    │   │   ├── loggeren.json
    │   │   └── tr.json
    │   ├── Promts/
    │   │   ├── cultivation-online_Prompt_A.txt
    │   │   ├── cultivation-online_Prompt_B.txt
    │   │   ├── cultivation-online_Prompt_C.txt
    │   │   ├── Technological-System_Prompt_C.txt
    │   │   ├── warpgame_Prompt_A.txt
    │   │   ├── warpgame_Prompt_B.txt
    │   │   └── warpgame_Prompt_C.txt
    │   └── themes/
    │       ├── dark.qss
    │       ├── light.qss
    │       ├── my_theme.json
    │       ├── system.json
    │       └── themes_meta.json
    ├── config/
    │   └── terminology.json
    ├── core/
    │   ├── __init__.py
    │   ├── ch-kontrol.py
    │   ├── chapter_check_worker.py
    │   ├── database_manager.py
    │   ├── file_list_manager.py
    │   ├── free_translators.py
    │   ├── kr-kontrol.py
    │   ├── llm_provider.py
    │   ├── localization.py
    │   ├── merge_controller.py
    │   ├── path_resolver.py
    │   ├── process_controller.py
    │   ├── project_manager.py
    │   ├── startup_worker.py
    │   ├── temizlik.py
    │   ├── theme_defaultCreate.py
    │   ├── theme_engine.py
    │   ├── token_controller.py
    │   ├── translation_controller.py
    │   ├── ui_state_manager.py
    │   ├── utils.py
    │   └── workers/
    │       ├── __init__.py
    │       ├── cleaning_worker.py
    │       ├── epub_worker.py
    │       ├── jsonoutput.py
    │       ├── local_token_count_worker.py
    │       ├── merging_worker.py
    │       ├── ml_terminology_extractor.py
    │       ├── ml_terminology_worker.py
    │       ├── prompt_generator.py
    │       ├── split_worker.py
    │       ├── text_utils.py
    │       ├── token_count_worker.py
    │       ├── token_counter.py
    │       ├── translation_error_check_worker.py
    │       └── translation_quality_checker.py
    ├── terminology/
    │   ├── __init__.py
    │   └── terminology_manager.py
    ├── ui/
    │   ├── __init__.py
    │   ├── api_key_editor_dialog.py
    │   ├── api_stats_dialog.py
    │   ├── app_settings_dialog.py
    │   ├── connection_bar_builder.py
    │   ├── dark_theme.py
    │   ├── dashboard_page.py
    │   ├── file_preview_dialog.py
    │   ├── file_table_interactions.py
    │   ├── file_table_manager.py
    │   ├── free_translators_dialog.py
    │   ├── gemini_version_dialog.py
    │   ├── mcp_server_dialog.py
    │   ├── menu_bar_builder.py
    │   ├── ml_terminology_range_dialog.py
    │   ├── new_project_dialog.py
    │   ├── project_page.py
    │   ├── project_settings_dialog.py
    │   ├── prompt_editor_dialog.py
    │   ├── request_counter_manager.py
    │   ├── right_panel_builder.py
    │   ├── sidebar_builder.py
    │   ├── splash_screen.py
    │   ├── split_dialogs.py
    │   ├── stats_chart_widget.py
    │   ├── status_bar_manager.py
    │   ├── terminology_dialog.py
    │   ├── terminology_page.py
    │   ├── text_editor_dialog.py
    │   ├── text_editor_page.py
    │   ├── theme_manager_dialog.py
    │   └── toast_widget.py
    └── wikiimg/
        └── readme.md

```

## Kök Dizin
- `CeviriUygulamasi.spec`: cx_Freeze / PyInstaller derleme yapılandırma dosyası.
- `dialogs.py`: Genel diyalog uygulamaları ve ortak pencere bileşenleri.
- `file-tree.md`: Proje dizin yapısı ve dosya açıklamaları belgesi.
- `LICENSE`: Proje lisans belgesi.
- `logger.py`: Günlük tutma yapılandırması ve merkezi loglama işlevleri.
- `main_window.py`: Ana uygulama penceresi ve uygulamanın giriş noktası.
- `main_window.spec`: cx_Freeze / PyInstaller derleme spesifikasyon dosyası.
- `README.md`: Türkçe kullanım kılavuzu ve proje tanıtım belgesi.
- `README-EN.md`: İngilizce kullanım kılavuzu (English documentation).
- `requirements.txt`: Python kütüphane bağımlılıkları listesi.
- `setup.py`: cx_Freeze ile Windows Portable .exe ve MSI kurulum paketi oluşturma betiği.
- `start.bat`: Uygulamayı terminal açmadan doğrudan başlatmak için Windows batch betiği.

## Uygulama Yapılandırması (`/AppConfigs`)
- `app_settings.json`: Genel uygulama tercihleri ve ayarları.
- `GVersion.ini`: Gemini model sürüm bilgileri.
- `MCP_Endpoints.json`: Yapılandırılmış MCP uç noktaları listesi.
- `APIKeys/`: API ve MCP erişim anahtarlarını depolama dizini (`APIKey1.txt`, `token1.txt`, `MCP/` vb.).
- `locales/`: Uygulama i18n ve log yerelleştirme dosyaları (`tr.json`, `en.json`, `logger.json`, `loggeren.json`).
- `Promts/`: Özel sistem istem (prompt) şablonları dizini.
- `themes/`: QSS stil dosyaları (`dark.qss`, `light.qss`), tema yapılandırmaları ve tema meta verileri (`themes_meta.json`).

## Proje Ayarları (`/config`)
- `terminology.json`: Proje geneli varsayılan terminoloji verileri.

## Çekirdek Modülü (`/core`)
- `__init__.py`: Paket başlatıcısı.
- `ch-kontrol.py`: Bölüm numarası ve sıra denetimi yardımcı araçları.
- `chapter_check_worker.py`: Bölüm tutarlılığını kontrol eden asenkron işçi.
- `database_manager.py`: SQLite veritabanı mimarisi ve anlık dosya indeksi yönetimi.
- `file_list_manager.py`: Proje dosya listesi alma, güncelleme ve veritabanı senkronizasyonu.
- `free_translators.py`: Ücretsiz çeviri servisleri (Google Translate, DeepL, Yandex) iş mantığı.
- `kr-kontrol.py`: Korece metin kontrol ve doğrulama aracı.
- `llm_provider.py`: LLM API'leri (Google Gemini, OpenAI / MCP) için ana sağlayıcı arayüzü.
- `localization.py`: Uygulama i18n (`tr()`) ve log yerelleştirme (`LogLocalizationManager`, `tr_log()`) modülü.
- `merge_controller.py`: Çevrilmiş bölümleri tek dosyada birleştirme kontrolcüsü.
- `path_resolver.py`: Eski ve yeni proje dosya hiyerarşisi yol çözümleyici.
- `process_controller.py`: Çeviri, kalite kontrol ve hata denetim ana süreç kontrolcüsü.
- `project_manager.py`: Proje oluşturma, yükleme ve yaşam döngüsü yönetimi.
- `startup_worker.py`: Uygulama açılışında arka plan tarama, SQLite otomatik migrasyon ve grafik ön yükleme işçisi.
- `temizlik.py`: Metin içi gereksiz karakter temizleme ve biçimlendirme araçları.
- `theme_defaultCreate.py`: Varsayılan tema dosyalarını otomatik oluşturma yardımcısı.
- `theme_engine.py`: Tema değiştirme ve dinamik stil uygulama motoru.
- `token_controller.py`: Token sayma, bütçe ve limit yönetim kontrolcüsü.
- `translation_controller.py`: Çekirdek çeviri iş akış yönetimi.
- `ui_state_manager.py`: Thread-safe kullanıcı arayüzü durum güncellemeleri.
- `utils.py`: Genel yardımcı fonksiyonlar.

### İşçiler (`/core/workers`)
- `__init__.py`: Paket başlatıcısı.
- `cleaning_worker.py`: Metin temizleme işlemleri için asenkron işçi.
- `epub_worker.py`: Dinamik isimlendirmeli (`[Proje]-X-Y.epub`) EPUB derleme işçisi.
- `jsonoutput.py`: JSON çıktı formatlama ve işleme yardımcısı.
- `local_token_count_worker.py`: Yerel/çevrimdışı token sayımı için asenkron işçi.
- `merging_worker.py`: Çevrilmiş dosyaları birleştirmek için asenkron işçi.
- `ml_terminology_extractor.py`: LLM tabanlı otomatik terminoloji çıkarma motoru.
- `ml_terminology_worker.py`: Terminoloji çıkarma görevlerini arka planda yürüten işçi.
- `prompt_generator.py`: LLM istemlerini (prompts) dinamik oluşturma mantığı.
- `split_worker.py`: Büyük roman dosyalarını bölme işçisi.
- `text_utils.py`: Metin işleme ve ayraç bölme yardımcı araçları.
- `token_count_worker.py`: Token sayımı için asenkron işçi.
- `token_counter.py`: Token hesaplama uygulaması.
- `translation_error_check_worker.py`: Çeviri sonrası satır sayısı ve eksik çeviri tespit işçisi.
- `translation_quality_checker.py`: Metin benzerliği (%80+), langdetect ve CJK kontrolü ile çok katmanlı kalite denetleyicisi.

## Terminoloji Yönetimi (`/terminology`)
- `__init__.py`: Paket başlatıcısı.
- `terminology_manager.py`: Terminoloji kayıtları için CRUD (Oluşturma, Okuma, Güncelleme, Silme) ve metin içi terminoloji enjeksiyonu yönetimi.

## UI Bileşenleri (`/ui`)
- `__init__.py`: Paket başlatıcısı.
- `api_key_editor_dialog.py`: API anahtarlarını ekleme/düzenleme diyaloğu.
- `api_stats_dialog.py`: API kullanım istatistikleri ve limit görüntüleme diyaloğu.
- `app_settings_dialog.py`: Uygulama genel ayarları (ayraçlar, promptlar, langdetect vb.).
- `connection_bar_builder.py`: Bağlantı ve servis çubuğu arayüz oluşturucu.
- `dark_theme.py`: Koyu tema renk ve stil tanımlamaları.
- `dashboard_page.py`: Ana Dashboard görünümü (grafik, bölüm satırına gitme, toplam istek kartı vb.).
- `file_preview_dialog.py`: Metin dosyalarını ve çevirileri önizleme penceresi.
- `file_table_interactions.py`: Tablo sağ tık menüsü (onaylı dosya silme, klasör açma) ve olay işleyicileri.
- `file_table_manager.py`: Proje dosya listesi tablosunun yönetimi ve sıralaması.
- `free_translators_dialog.py`: Ücretsiz çeviri servisleri ve Proxy ayarları penceresi.
- `gemini_version_dialog.py`: Gemini model sürümlerini seçme diyaloğu.
- `mcp_server_dialog.py`: MCP sunucu ve uç nokta yapılandırma penceresi.
- `menu_bar_builder.py`: Üst menü çubuğu (Menu Bar) bileşeni oluşturucu.
- `ml_terminology_range_dialog.py`: ML terminoloji çıkarıcı için bölüm aralığı seçim diyaloğu.
- `new_project_dialog.py`: Yeni proje oluşturma sihirbazı ve API/MCP uyarı sistemi.
- `project_page.py`: Proje yönetimi ve detay sayfası.
- `project_settings_dialog.py`: Projeye özel yapılandırma ayarları penceresi.
- `prompt_editor_dialog.py`: Sistem istemlerini düzenleme penceresi.
- `request_counter_manager.py`: Günlük API istek sayacı ve istatistik yöneticisi.
- `right_panel_builder.py`: Sağ kontrol paneli arayüz bileşenleri.
- `sidebar_builder.py`: Sol gezinme menüsü (Sidebar) oluşturucu.
- `splash_screen.py`: Modern açılış (Splash) ekranı widget'ı.
- `split_dialogs.py`: Dosya bölme pencere diyalogları.
- `stats_chart_widget.py`: Dashboard istek istatistik grafiği widget'ı.
- `status_bar_manager.py`: Alt durum çubuğu (Status Bar) mesaj ve durum yönetimi.
- `terminology_dialog.py`: Terminoloji ekleme ve düzenleme penceresi.
- `terminology_page.py`: Terminoloji yönetimi ana sayfası.
- `text_editor_dialog.py`: Dahili metin düzenleyici diyalog penceresi.
- `text_editor_page.py`: Dahili metin düzenleyici ana sayfası.
- `theme_manager_dialog.py`: Tema yönetimi ve özelleştirme diyaloğu.
- `toast_widget.py`: Anlık bildirim (Toast) mesajları widget'ı.

## Görseller (`/wikiimg`)
- `readme.md`: Wiki ve dokümantasyon görselleri kılavuzu.

