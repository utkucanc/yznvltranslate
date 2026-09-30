# Novel Çeviri Aracı - Yapay Zeka Destekli Novel Çeviri ve Düzenleme Uygulaması
[![GitHub Issues](https://img.shields.io/github/issues/utkucanc/yznvltranslate?label=Open%20Issues)](https://github.com/utkucanc/yznvltranslate/issues)
[![downloads](https://img.shields.io/github/downloads/utkucanc/yznvltranslate/total?label=Total%20Downloads)](https://github.com/utkucanc/yznvltranslate/releases)
[![downloads-latest](https://img.shields.io/github/downloads/utkucanc/yznvltranslate/latest/total?label=Latest%20release)](https://github.com/utkucanc/yznvltranslate/releases/latest)
## License
[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2Futkucanc%2Fyznvltranslate.svg?type=large)](https://app.fossa.com/projects/git%2Bgithub.com%2Futkucanc%2Fyznvltranslate?ref=badge_large)

Discord : Utkucanc
# NCA (Novel Çeviri Aracı v3.1.1)

Bu proje, yabancı dildeki (özellikle Çince, Korece, İngilizce vb.) web romanlarını (novel) yerel ortamda organize etmek, yapay zeka (Google Gemini, OpenAI/MCP) ve klasik çeviri sağlayıcıları (DeepL, Yandex, Google Translate) kullanarak toplu çevirisini yapmak, metin içi terminoloji entegrasyonu sağlamak ve sonuçları temizleyip EPUB/TXT formatlarında birleştirmek için tasarlanmış, PyQt6 tabanlı modern bir masaüstü uygulamasıdır.

## Nasıl Kullanılır?
- [![Youtube Video Link](https://img.shields.io/badge/Youtube%20Video%20Link-red?style=for-the-badge&logo=youtube)]((https://youtu.be/V2B7o9dDJvM))
- [https://youtu.be/4HQpAn_qiBU](https://youtu.be/V2B7o9dDJvM)

---

## 🚀 Öne Çıkan Özellikler

* **SQLite Veri Tabanı & Yüksek Performans (v3.1.1)**:
  - Projenin dosya durumları ve yolları SQLite veri tabanı üzerinde anlık olarak indekslenir.
  - Açılış süresi ve dosya listesi yüklemeleri OS filesystem taraması yapılmadan milisaniyeler seviyesine indirilmiştir.
  - Veri tabanı kullanmayan eski projeler açıldığında otomatik tespit edilerek verileri eksiksiz veri tabanına aktarılır (otomatik migrasyon).
  - Tamamlanan çeviriler bekletilmeden anında veri tabanına işlenir.

* **Log Yerelleştirme Altyapısı (v3.1.1)**:
  - Tüm sistem ve arayüz log mesajları ayrıştırılarak Türkçe ve İngilizce (`logger.json` / `loggeren.json`) olarak yerelleştirildi.
  - f-string ve değişken içeren log mesajları dinamik regex desen eşlemesi (pattern matching) ile çalışma zamanında İngilizce karşılıklarına dönüştürülür.

* **Gelişmiş Dosya ve Kullanıcı Etkileşimleri (v3.1.1)**:
  - **Bölüme/Satıra Git:** Liste filtrelenmeden girilen bölüm numarasına otomatik kaydırma (scroll to row) yapılır ve ilgili satır vurgulanır.
  - **Dinamik EPUB İsimlendirmesi:** Oluşturulan EPUB dosyaları otomatik olarak `[ProjeAdı]-[İlkBölüm]-[SonBölüm].epub` (örn. `TestProje-1-500.epub`) formatında kaydedilir.
  - **Sağ Tık Menüsünden Dosya Silme:** Proje dosya listesinde sağ tık menüsüne onay diyalog kutulu dosya silme özelliği eklendi.
  - **Düzeltilmiş İstatistik Grafiği & Splash Ekranı:** Dashboard günlük grafik çizimi, toplam istek sayısı takibi ve açılıştaki siyah/beyaz donmayı engelleyen arka plan yüklemeli Splash ekranı entegre edildi.

* **Çoklu Çeviri Sağlayıcı Desteği (v3.0.0)**:
  - **Yapay Zeka (LLM / MCP):** Google Gemini (`google-genai`), OpenAI uyumlu MCP (Multi-endpoint Connection Provider) sunucu mimarisi ve rotasyonlu API Key Havuzu.
  - **Klasik Çeviri Servisleri:** DeepL, Yandex Translate ve Proxy destekli (HTTP / HTTPS / SOCKS4 / SOCKS5) Google Translate.
  - **Otomatik Key Rotasyonu:** 429 Kota aşımı alındığında havuzdaki sıradaki anahtara veya endpoint'e otomatik geçiş.

* **Gelişmiş Metin İçi Terminoloji Sistemi (v3.0.0 & v3.1.0)**:
  - **Metin İçi Enjeksiyon:** Kayıtlı terimler isteğe gönderilmeden önce doğrudan kaynak metne yerleştirilir. Bu sayede AI terimleri doğru Türkçe eklerle doğal bir şekilde bağlama oturtur ve %80'e varan token tasarrufu sağlanır.
  - **Bölüm Aralıklı Terminoloji Çıkarma:** ML tabanlı otomatik terim çıkarıcı ile belirlenen bölüm aralıklarındaki en önemli özel isim ve teknikler otomatik tespit edilip sözlüğe eklenir.

* **Esnek Ayarlar ve Prompt Yönetimi (v3.1.0 & v3.1.1)**:
  - **Uygulama İçi Prompt Düzenleme:** Prompt Generator ve ML Terminoloji Çıkarıcı için kullanılan sistem promptları uygulama içinden doğrudan düzenlenebilir.
  - **Özelleştirilebilir Ayraçlar:** Bölüm birleştirme (`export_separator`) ve toplu bölüm parçalama (`split_separator`) ayraçları dinamik olarak ayarlanabilir.
  - **Langdetect & Satır Kontrolü:** Kalite kontrol için Langdetect kaynak/hedef dili ayarlanabilir; düşük satır sayılı dosyalar tespit edilip raporlanır.

---

## 📋 Gereksinimler

Programın kaynak koddan çalıştırılabilmesi için sisteminizde aşağıdaki kütüphanelerin yüklü olması gerekir:

```bash
pip install -r requirements.txt
```
- Tavsiye edilen Python sürümü: **Python 3.13**

---

## 🛠️ Kurulum ve Çalıştırma

### 1- Geliştirici Ortamı (Python) ile Çalıştırma:
Gerekli bağımlılıkları yükledikten sonra terminalde proje dizinindeyken:
```bash
python main_window.py
```
komutu ile arayüzü başlatabilirsiniz.

### 2- Windows İçin Portable .EXE / MSI Kurulumu Alma:
Projeyi `cx_Freeze` ile derleyerek Python gerektirmeyen bağımsız bir Windows uygulaması haline getirebilirsiniz.

**Taşınabilir (Portable) Klasör Derlemesi:**
```bash
python setup.py build
```
Çıktı `build/NovelCeviriAraci-Portable/` klasöründe `CeviriUygulamasi.exe` olarak oluşturulur.

**Windows MSI Kurulum Dosyası (Setup Installer):**
```bash
python setup.py bdist_msi
```
Çıktı `dist/` klasörü altında `NovelCeviriAraci-3.1.1-win64.msi` olarak hazırlanır.

---

## 📁 Proje Dizin Yapısı

Uygulama, genel yapılandırma ve tema dosyalarını `AppConfigs` klasöründe saklar:
* `AppConfigs/locales/`: Dil dosyaları (`tr.json`, `en.json`, `logger.json`, `loggeren.json`).
* `AppConfigs/themes/`: Tema şablonları ve QSS özelleştirmeleri.
* `AppConfigs/app_settings.json`: Uygulama geneli ayarlar.
* `AppConfigs/app.log`: Günlük izleme ve hata kayıtları.

Yeni projeler `Project/<ProjeAdı>/` dizini altında otomatik oluşturulur:
- `download/`: Orijinal ham metin dosyaları.
- `translate/`: Çevrilmiş metin dosyaları.
- `completed/`: Birleştirilmiş `.txt` ve `.epub` çıktıları.
- `config/`: Projeye özel `config.ini` ve `terminology.json` verileri.

---

## 📜 Sürüm Geçmişi (Changelog)

| Sürüm | Değişiklikler |
|-------|--------------|
| 3.1.1 | **SQLite Veri Tabanı Mimarisi & Otomatik Migrasyon:** Proje dosya takibi OS dosya taramasından SQLite veritabanına taşındı; açılış ve erişim hızlandırıldı, eski projeler otomatik aktarıldı. **Log Yerelleştirme Altyapısı (Log Localization):** Tüm log mesajları ayrıştırılarak `tr`/`en` dinamik çeviri ve regex f-string parametre eşleme altyapısı kuruldu. **Satıra/Bölüme Gitme Özelliği:** Liste filtrelenmeden girilen bölüm satırına otomatik scroll yapma ve vurgulama eklendi. **Dinamik EPUB İsimlendirmesi:** Birleştirilen EPUB çıktıları `[ProjeAdı]-[İlkBölüm]-[SonBölüm].epub` formatına kavuşturuldu. **Onaylı Dosya Silme:** Tablo sağ tık menüsüne onay iletişim kutulu dosya silme eklendi. **Grafik ve UI İyileştirmeleri:** Dashboard grafik yenileme, toplam istek sayısı takibi, splash ekranı, proxy diyalog boyutları ve yeni proje API/MCP uyarıları düzenlendi. **Kalite & Hata Kontrolü:** Langdetect dili özelleştirme ve düşük satır sayılı dosyaları denetleyip raporlama özellikleri eklendi. |
| 3.1.0 | **Yeni Proje Mimarisi & Geriye Uyumlu Klasör Yapısı:** Projeler `Project/<ProjeAdı>/` dizininde düzenli isimlerle (`completed`, `config`, `download`, `translate`) oluşturulur; eski yapılar geriye dönük uyumla (`path_resolver`) desteklenir. **Prompt Düzenleme:** Prompt Generator ve ML Terminoloji için sistem promptları App Settings üzerinden doğrudan düzenlenebilir. **Dinamik Ayraçlar:** Split ve Export ayraçları ayarlardan özelleştirilebilir. **İndirme Temizliği:** Karmaşık Selenium/Web scraping kodları temizlendi, arayüz hafifletildi. **Tam Lokalizasyon:** Terminoloji sayfası ve tüm yeni bileşenler i18n (`tr()`) ile Türkçe/İngilizce olarak tamamlandı. |
| 3.0.0 | **Yenilenmiş Koyu UI:** Dashboard, Proje detay paneli ve gömülü Terminoloji/Metin Editörü sayfaları ile kart tabanlı yeni tasarım. **Metin İçi Terminoloji Enjeksiyonu:** Terimler AI'a gönderilmeden önce metne enjekte edilerek %80 token tasarrufu ve daha akıcı çekimleme sağlandı. **Yeni Çeviri Sağlayıcıları:** DeepL, Yandex Translate, Google Translate ve Proxy (SOCKS/HTTP) desteği eklendi. Stabil çalışmayan çeviri önbelleği (cache) kaldırıldı. |
| 2.6.0 | **Gelişmiş Çeviri Hata Kontrolü:** İngilizce ve Latin alfabesi kullanan kaynak diller için Metin Benzerlik Oranı (%80+) ve `langdetect` Dil Tespiti entegrasyonu sağlandı. |
| 2.5.0 | **Lokalizasyon çalışması başlatıldı:** İngilizce ve Türkçe dil seçenekleri altyapısı eklendi. |
| 2.4.0 | Offline Token Sayımı, Tema Dosyalarının Otomatik Oluşturulması, MCP Diyalog İyileştirmeleri, ML Terminoloji Bölüm Aralığı Seçimi. |
| 2.3.0 | Yeni Arayüz Tasarımı ve Tema Düzenleme Paneli. |
| 2.1.0 | Paragraf Bazlı Çeviri, Toplu Çeviri (Batch Mode) ve Asenkron (Paralel) Çeviri Desteği. |
| 2.0.0 | MCP Mimarisi, Prompt Generator, Translation Cache, Terminology Memory, Yeni GenAI SDK, CJK Çeviri Hata Kontrolü. |
| 1.9.9 | `logger.py` ile Otomatik Loglama Sistemi, Donma ve Token Kaybı Düzeltmeleri. |
| 1.9.8 | Çalışmayı etkileyen genel hatalar giderildi (retry_count, statusLabel wordwrap, cx_Freeze base). |
| 1.9.7 | Toplu bölüm ekleme (`split_worker.py`) özelliği eklendi. |
| 1.9.6 | JS dosyalarını kaydetme özelliği (JS Save menüsü) eklendi. |
| 1.9.5 | Seçili dosyaların EPUB dosyası olarak kaydı sağlandı. |
| 1.9.4 | Çevirilecek dosya sayısının sınırlandırılması (`file_limit`) getirildi. |
| 1.9.3 | Bölüm başlığı kontrolü getirildi. |

![alt](https://github.com/utkucanc/yznvltranslate/blob/main/diagram.png?raw=true)
