# Novel Çeviri Aracı - Yapay Zeka Destekli Novel Çeviri ve Düzenleme Uygulaması
[![GitHub Issues](https://img.shields.io/github/issues/utkucanc/yznvltranslate?label=Open%20Issues)](https://github.com/utkucanc/yznvltranslate/issues)
[![downloads](https://img.shields.io/github/downloads/utkucanc/yznvltranslate/total?label=Total%20Downloads)](https://github.com/utkucanc/yznvltranslate/releases)
[![downloads-latest](https://img.shields.io/github/downloads/utkucanc/yznvltranslate/latest/total?label=Latest%20release)](https://github.com/utkucanc/yznvltranslate/releases/latest)
# NCA

Bu proje, yabancı dildeki (özellikle İngilizce, Korece, Çince gibi) web romanlarını (novel) indirmek, Google Gemini API kullanarak yerel bağlantıda toplu çevirisini yapmak ve sonrasında bu metinleri temizleyip EPUB veya benzeri formatlarda birleştirmek için tasarlanmış, PyQt6 tabanlı masaüstü bir uygulamadır.
## Nasıl Kullanılır?
- [![Youtube Video Link](https://img.shields.io/badge/Youtube%20Video%20Link-red?style=for-the-badge&logo=youtube)](https://youtu.be/4HQpAn_qiBU)
- https://youtu.be/4HQpAn_qiBU
## Özellikler

* **Toplu İndirme**: 
  - Standart Web Kazıma (Requests/BS4)
  - JavaScript destekli indirme (Novelfire, Booktoki ve 69shuba için Selenium Webdriver entegrasyonu)
* **Gelişmiş Çeviri Sistemi**: 
  - OpenAI uyumlu sunucu desteği ve Google Gemini (`google-genai`) ile çalışan **MCP (Multi-endpoint Connection Provider)** mimarisi.
  - Sınırsız sayıda API Anahtarından oluşan rotasyonlu Key Pool desteği.
  - Otomatik **Translation Cache** ve **Terminology Memory** ile maliyet tasarrufu ve terim tutarlılığı.
  - **Prompt Generator (PromtGen)** ile projeye özel (Literal/Natural/Balanced) çeviri promptlarının AI tarafından otomatik çıkarılması.
  - Çevirilerde Çince/Korece (CJK) oranını tarayarak hatalı çıktıları engelleyen karakter koruma sistemi.
  - **Paragraf Bazlı Çeviri (v2.1.0):** Cache aktif olsun olmasın her dosya otomatik olarak paragraflara bölünür; her paragraf bağımsız çevrilip birleştirilir. Büyük dosyalarda token verimliliğini artırır.
  - **Asenkron Çeviri (V2.1.0):** Proje ayarları kısmından sayısı düzenlenebilir paralel çeviri sistemi. Aynı anda API isteği göndererek birden fazla dosyanın çeviri yapılabilmesine imkan sağlar.(Gemini için worker sayısı 3 tavsiye edilmektedir. 3 Worker RPM değeri 11-12 aralığındadır.)
  - **Toplu Çeviri / Batch Mode (v2.1.0 - Test):** Birden fazla bölümü `===CHAPTER_START===` / `===CHAPTER_END===` ayraçlarıyla tek bir API isteğine paketler. Aynı RPD kotasıyla daha fazla bölüm çevrilmesini sağlar. Parse başarısız olursa otomatik tekli moda düşer.
* **Dosya Manipülasyonu**:
  - `Toplu Bölüm Ekle`: Büyük boyutlu `.txt` dosyalarını "## Bölüm - X ##" ayracı baz alınarak otomatik parçalara ayırma.
  - Geliştirilmiş çift tıklama ile açılan Metin Düzenleyici (Text Editor) üzerinden anlık düzeltme.
  - Çevrilmiş bölümleri tek bir `.txt` veya `.epub` formatında birleştirme.
* **Token ve Limit Sayacı**: Akıllı durum çubuğu ile maliyet hesaplama, hız takibi ve kalıcı API istek istatistikleri. Grafik ve tablo olarak api istek sayısı listeleme.

## Gereksinimler

Programın kaynak koddan çalıştırılabilmesi için sisteminizde aşağıdaki kütüphanelerin yüklü olması gerekir:

```bash
pip install -r requirements.txt
```
- Tavsiye edilen Python versiyonu:
```bash
Python 3.13 
```
  
Not: JavaScript tabanlı Booktoki ve 69shuba indirmelerini (Selenium) kullanmak için bilgisayarınızda Google Chrome tarayıcısı yüklü olmalıdır. `webdriver-manager` aracı ChromeDriver eşleştirmelerini kendi kendine yapacaktır.

## Kurulum ve Çalıştırma

### 1- Geliştirici Ortamı (Python) ile Çalıştırma:
Gerekli bağımlılıkları yükledikten sonra komut satırında proje dizinindeyken:
```bash
python main_window.py
```
komutu ile arayüzü başlatabilirsiniz.

### 2- Windows İçin Kullanıma Hazır .EXE (Build) Alma:
Projeyi `cx_Freeze` ile derleyerek, Python yüklü olmayan Windows cihazlarda da çalışabilen bir çalıştırılabilir dosya haline getirebilirsiniz.

Derleme (build) klasörü oluşturmak için:
```bash
python setup.py build
```
Çıkan dosyalar `build/` klasörü içerisinde `CeviriUygulamasi.exe` olarak belirecektir.

Tıklayıp kurulan bir MSI Kurulum Dosyası (Installer) oluşturmak isterseniz:
```bash
python setup.py bdist_msi
```
komutunu kullanabilirsiniz. İşlem tamamlandıktan sonra proje dosyalarınızın içerisindeki `dist/` klasöründe kurulum dosyasına erişebilirsiniz.

## Proje Yapısı

Uygulamanın düzgün çalışabilmesi için veritabanı benzeri dosyaları `AppConfigs` isimli bir klasör hiyerarşisinde saklamaktadır:
* `AppConfigs/APIKeys/`: Yeni projelerde veya genel uygulamada kullanılacak `.txt` formatındaki Gemini API Anahtarlarını tutar.
* `AppConfigs/Promts/`: Çeviride veya metin düzeltmelerinde kullanılan yapay zeka yönlendirme (promt) dosyalarını saklar.

Her "Yeni Proje" oluşturduğunuzda uygulama, uygulamanın kurulu olduğu dizinde veya seçtiğiniz hedefte o projeye özel alt klasörler oluşturur (`dwnld`, `trslt`, `cmplt` vs.) ve indirmeleri, çevirileri birbirine karışmadan bu ortamların içinde saklar. 

## JS Dosyalarını Tarayıcıda Elle Kullanma
Uygulamanın içindeki üst gezinti çubuğunda yer alan **JS Save** menüsüne tıklayarak Booktoki.js ve 69shuba.js komut dosyalarını kolayca Masaüstünüze alabilirsiniz. Eğer indirme aracını kullanmak yerine direkt tarayıcıyı tercih ediyorsanız; ilgili romanın okuma sayfasına girip, Geliştirici Seçeneklerini (`F12`) açarak **Konsol** sekmesine bu indirilen JS kodlarını kopyalayıp enter'a basmanız yeterlidir. Kod, tüm bölümleri kendi kendine tarayıp size bir metin dosyası indirecektir.

## Loglama Sistemi
Sürüm 1.9.9 itibarıyla uygulama, çalışma sürecindeki tüm önemli olayları, uyarıları ve hataları otomatik olarak `AppConfigs/app.log` dosyasına kaydeder. Herhangi bir hata ile karşılaşırsanız bu dosyayı inceleyerek sorunun kaynağını kolayca tespit edebilirsiniz. Log dosyası her uygulama başlatıldığında üzerine ekleme yapılarak güncellenir (üzerine yazılmaz).

## Proje Yapısı

Uygulamanın düzgün çalışabilmesi için veritabanı benzeri dosyaları `AppConfigs` isimli bir klasör hiyerarşisinde saklamaktadır:
* `AppConfigs/APIKeys/`: Yeni projelerde veya genel uygulamada kullanılacak `.txt` formatındaki Gemini API Anahtarlarını tutar.
* `AppConfigs/Promts/`: Çeviride veya metin düzeltmelerinde kullanılan yapay zeka yönlendirme (promt) dosyalarını saklar.
* `AppConfigs/app.log`: Uygulama genelinde oluşturulan log/izleme dosyası. Hata ayıklama için kullanışlıdır. *(v1.9.9)*

Her "Yeni Proje" oluşturduğunuzda uygulama, uygulamanın kurulu olduğu dizinde veya seçtiğiniz hedefte o projeye özel alt klasörler oluşturur (`dwnld`, `trslt`, `cmplt` vs.) ve indirmeleri, çevirileri birbirine karışmadan bu ortamların içinde saklar.
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
## Sürüm Geçmişi

| Sürüm | Değişiklikler |
|-------|--------------| 
| 2.1.0 | **SRP** yeniden yapılandırma. **Paragraf Bazlı Çeviri** standart hale getirildi (cache bağımsız). **Toplu Çeviri (Batch Mode)** eklendi: birden fazla bölümü tek API isteğinde göndererek aynı RPD ile daha fazla bölüm çevirme. **Asenkron Çeviri** eklendi. Aynı anda birden fazla API isteği göndererek daha hızlı çeviri yapılabilir. Proje Ayarlarından aktif/deaktif edilebilir. |
| 2.0.0 | Majör Güncelleme! MCP Mimarisi, Prompt Generator, Translation Cache, Terminology Memory, Yeni GenAI SDK, CJK Çeviri Hata Kontrolü ve gelişmiş Metin Düzenleyicisi eklendi. |
| 1.9.9 | Uygulama genelinde `logger.py` ile loglama sistemi eklendi. Token sayımı sonrasında oluşan UI donma hatası giderildi. Token verisi kısmi sayımda sıfırlanma (veri kaybı) sorunu çözüldü. |
| 1.9.8 | Çalışmayı etkileyen genel hatalar giderildi (retry_count, statusLabel wordwrap, cx_Freeze base). |
| 1.9.7 | Toplu bölüm ekleme (`split_worker.py`) özelliği eklendi. |
| 1.9.6 | JS dosyalarını kaydetme özelliği (JS Save menüsü) eklendi. |
| 1.9.5 | Seçili dosyaların EPUB dosyası olarak kaydı sağlandı. |
| 1.9.4 | Çevirilecek dosya sayısının sınırlandırılması (`file_limit`) getirildi. |
| 1.9.3 | Bölüm başlığı kontrolü getirildi. |
