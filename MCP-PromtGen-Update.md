# MCP & Prompt Generator (PromtGen) Güncelleme Planı

Bu güncelleme, uygulamaya iki ana özellik eklemeyi hedefler:
1. **MCP (Multi-endpoint Connection Provider)**: Farklı yapay zeka servislerine ve yerel LLM'lere bağlanabilme altyapısı.
2. **Prompt Generator (PromtGen)**: Mevcut hikaye içeriği, wiki ve kayıtlı promtlardan yararlanarak projeye özel optimize edilmiş çeviri promtu üretme sistemi.

---

## 1. MCP (Multi-endpoint Connection Provider)

Bu güncelleme, uygulamanın yalnızca Google Gemini ile sınırlı kalmayıp, yerel LLM'ler (LM Studio, Ollama, LocalAI), OpenRouter veya diğer OpenAI uyumlu servisleri (OpenAI, Anthropic, DeepSeek vb.) kullanabilmesini sağlayacak bir altyapı eklemeyi hedefler.

### Veri Yapısı ve Depolama
Bağlantı ayarları `AppConfigs/MCP_Endpoints.json` dosyasında, API anahtarları ise her bağlantı ID'sine özel ayrı dosyalarda saklanacaktır. Bu yapı, **tek bir model için birden fazla API anahtarı (key pool)** kullanımına olanak tanır.

> [!IMPORTANT]
> API Anahtarları artık JSON içinde değil, `AppConfigs/APIKeys/MCP/<endpoint_id>.txt` yolundaki dosyalarda saklanır. Dosya içindeki her bir satır farklı bir API anahtarı olarak kabul edilir.
LLM ekosisteminde yakında şunlar olacak:

- OpenAI
- Anthropic
- Gemini
- OpenRouter
- Ollama
- LM Studio
- LocalAI
- Groq
- TogetherAI
- DeepSeek
- vLLM


**Örnek Standart JSON Formatı:**
```json
{
  "active_endpoint_id": "default_gemini",
  "endpoints": [
    {
      "id": "default_gemini",
      "name": "Standart Gemini",
      "type": "gemini",
      "model_id": "gemini-2.5-flash-preview-09-2025",
      "base_url": null,
      "use_key_rotation": true,
      "headers": {}
    },
    {
      "id": "openrouter_service",
      "name": "OpenRouter (Claude/GPT-4)",
      "type": "openai_compatible",
      "model_id": "google/gemini-2.0-flash-001",
      "base_url": "https://openrouter.ai/api/v1",
      "use_key_rotation": false,
      "headers": {
        "HTTP-Referer": "https://github.com/UtkuCanC/yznvltranslate",
        "X-Title": "YZ Novel Translate"
      }
    }
  ]
}
```
#### Parametre Açıklamaları:
- `id`: Her bağlantı için benzersiz bir kimlik. Anahtar dosyası bu ID ile eşleşir (`<id>.txt`).
- `type`: `gemini` veya `openai_compatible`.
- `model_id`: Hedef modelin teknik adı.
- `base_url`: API servis adresi.
- `use_key_rotation`: Eğer `true` ise, dosyadaki anahtarlar sırayla veya rastgele kullanılır.
- `headers`: İsteğe bağlı HTTP başlıkları.

#### Anahtar Yönetimi (MCP Keys):
- Yol: `AppConfigs/APIKeys/MCP/`
- Örnek: `default_gemini.txt` içeriği:
  ```text
  apikey_1_buraya
  apikey_2_buraya
  apikey_3_buraya
  ```
- Uygulama, belirtilen ID'ye ait dosyayı okur ve içindeki tüm geçerli anahtarları bir "havuz" olarak kullanır.


### Arayüz (UI)
#### A. MCP Sunucu Yönetim Paneli
`dialogs.py` içerisinde `MCPServerDialog` sınıfı oluşturulacak:
- **Liste**: Kayıtlı sunucuları sol tarafta listeler.
- **Form**: Sağ tarafta ad, tür, URL ve Model ID alanları.
- **Anahtar Editörü**: İlgili sunucuya ait anahtarları (her satıra bir tane) ekleyip düzenleyebileceğiniz bir `QTextEdit` alanı.
- **Hızlı Test**: Havuzdaki rastgele bir anahtar veya seçili anahtar ile bağlantı testi.

#### B. Ana Pencere Entegrasyonu
- Üst menü barına veya ayarlar kısmına "Yapay Zeka Kaynağı" (AI Source) seçeneği eklenecek.
- Aktif seçilen kaynak, tüm uygulama genelinde (Token Sayacı ve Çeviri) kullanılacak.

#### C. Proje Bazlı Seçim
- Proje ayarları içerisinde "Bu proje için özel bağlantı kullan" seçeneği eklenecek. Böylece bazı projeler Gemini ile, bazıları yerel model ile çevrilebilir.

---

## 2. Prompt Generator (PromtGen)

Proje bazlı, hikayenin ruhuna ve terimlerine en uygun çeviri promtunu otomatik olarak üretmek için tasarlanmış bir yapay zeka asistanıdır.

### Özellikler ve Çalışma Mantığı

#### A. Bağlam (Context) Derleme
Yapay zekaya gönderilecek bağlam şu verilerden oluşturulur:
1. **Kayıtlı Promtlar**: Uygulama içindeki mevcut başarılı promtlar örnek olarak AI'ya sunulur.
2. **Wiki İçeriği**: Eğer projede bir wiki metni girildiyse, karakter isimleri ve evren kurallarını içermesi için derlenir.
3. **Bölüm Örnekleri (2+2+2 Metodu)**: Eğer wiki içeriği girilmemiş ise çevirisi yapılmamış bölümlerden;
   - Baştan 2 bölüm,
   - Ortadan 2 bölüm,
   - Sondan 2 bölüm,
   alınarak hikayenin genel tonu ve yazım dili analiz edilir.

#### B. Promt Üretimi
Bütün bu veriler derlenerek, seçili aktif LLM üzerinden "Bu hikaye için en iyi çeviri promtunu oluştur" talimatı ile yeni bir promt üretilir.
PromtGen sadece 1 prompt üretmesin.

3 prompt üretsin.

- Prompt A – literal
- Prompt B – natural
- Prompt C – balanced

Kullanıcı seçsin.

#### C. Kayıt ve Kullanım
Oluşturulan promt otomatik olarak **`ProjeAdı-PromtGen.txt`** adıyla kaydedilir ve proje ayarlarında seçilebilir hale gelir.

#### D. Arayüz (UI) Entegrasyonu
- **Proje Ayarları**: "Prompt Oluşturucu (Generator)" adında yeni bir buton eklenecek.
- **Generator Ekranı**: Wiki metni giriş alanı ve hangi bölümlerin örnek alınacağını seçme (varsayılan 2+2+2) seçeneklerini içeren bir pencere.

---

## 3. Teknik Mimari

- **LLMProvider Soyutlama**: Hem çeviri hem de promt üretimi için kullanılacak ortak bir API katmanı.
- **PromptGenerator Sınıfı**: Dosya okuma (2+2+2 metodu) ve bağlam hazırlama mantığını yürüten yeni bir backend sınıfı.

---

## 4. Uygulama Adımları

1. **Hazırlık**: MCP altyapısının kurulması (JSON ve Key Pool).
2. **PromtGen Backend**: Bölüm örnekleme mantığının (baştan, ortadan, sondan dosya seçimi) yazılması.
3. **UI Tasarımı**: MCP Server yönetimi ve Prompt Generator pencerelerinin kodlanması.
4. **Entegrasyon**: Üretilen promtun proje ayarlarına otomatik bağlanması.
5. **Test**: Farklı hikaye türleri için üretilen promtların başarısının ölçülmesi.

---
## 5. Ek Düzenlemeler
- **API Health Check**: Proje Ayarları kısmından api durumu kontrol edilecek. Kotası dolu ise uyarı verecek. Bu kontrol mümkünse kotayı düşürmemeli.
- **Token Sayacı**: MCP entegrasyonu ile birlikte token sayacı güncellenecek.
- **Çeviri Arayüzü**: MCP entegrasyonu ile birlikte çeviri arayüzü güncellenecek.
- **UI Düzenlemeleri**:
    - İndirme yönetimi kısmında yer alan açıl pencerenin arka planı koyulaştırılacak. Şeffaf olması okunmayı zorlaştırıyor.
    - Başlık kontrolü butonu kaldırılacak bu buton yerine çıktı txt dosyalarının içeriğindeki korece ve çince kelime kontrolü yapan "Çeviri Hata Kontrol" butonu eklenecek.
- **Çeviri Hata Kontrolü**: Çıktı txt dosyalarının içeriğindeki korece ve çince kelime kontrolü yapan bir buton eklenecek. 
    - Butona tıklandığında çıktı klasöründeki tüm txt dosyaları kontrol edilecek. 
    - ratio = korece_karakter_sayısı / toplam_karakter_sayısı && ratio = çince_karakter_sayısı / toplam_karakter_sayısı
    - Korece ve çince karakter sayısı **ratio > 5%** olan dosyalar silinecek. Onay penceresi çıkacak. (... Silinsin mi ? | Evet | Hayır)
    - Onay penceresi içerisinde silinecek dosya sayısı ve toplam karakter sayısı yazacak.
    - Korece ve çince karakter sayısı **ratio < 5%** olan dosyalar silinmeyecek.
    - Korece ve çince karakter sayısı **ratio < 5%** olan dosyalar için bir rapor dosyası oluşturulacak.
    - Korece ve çince karakter sayısı **ratio > 5%** olan dosyalar için bir rapor dosyası oluşturulacak.
    - ch-kontrol.py ve kr-kontrol.py dosyaları kullanılacak.
    - ch-kontrol.py dosyası korece karakter sayısını kontrol edecek.
    - kr-kontrol.py dosyası çince karakter sayısını kontrol edecek.
    - Bu dosyalar programa uygun hale getirilecek ve uygun worker dosyası oluşturulacak.
- **Çeviriyi Durdurma Butonu**: Çeviri işlemi sırasında çeviriyi durdurmak için bir buton eklenecek.
    - Butona tıklandığında çeviri işlemi durdurulacak.
    - Bu buton çeviri işlemi devam ederken görünür olacak. Çeviri işlemi bittiğinde veya durdurulduğunda kaybolacak. Çeviriyi başlat butonu tıklandığında bu buton görünür olacak. Duraklat butonunun boyu küçültülecek. Durdurma butonu kırmızı renkte olacak. Tıklandığında uyarı mesajı verilecek. 
- **Projeler listesi**: Projeler listesinin üstünde arama çubuğu eklenecek. Bu çubuğa yazılan kelime projeler listesinde aranacak ve bulunan projeler listelenecek. Yazılan metini temizlemek için bir buton eklenecek.
- **Proje içinde dosya arama**: Ana UI içindeki dosya listesi kısmında arama çubuğu eklenecek. Bu çubuğa yazılan kelime dosya listesinde aranacak ve bulunan dosyalar listelenecek. Yazılan metini temizlemek için bir buton eklenecek.
- **Uygulama bilgi alt barı**: Uygulamanın en altında bir bar eklenecek. Bu barın içerisinde şu bilgiler küçük bir şekilde yer alacak
    - Mevcut durum (Hazır - Çeviri yapılıyor - Duraklatıldı - Durduruldu - Hata var ...)
    - Çeviri hızı (bölüm/saat)
    - Kullanılan model
    - Kullanılan API Kayıtlı Adı
    - Kullanılan API servisi
    - Kullanılan API istek sayısı
    - Kullanılan API token sayısı
    - En sol köşe UI Yeniden yükleme butonu eklenecek. Bu buton tıklandığında UI yeniden yüklenecek.
---
## 6. Translation Cache

Bu doküman, YZNovelTranslate projesine eklenmesi planlanan **Translation
Cache** ve **Terminology Memory** sistemlerinin mimari tasarımını, veri
yapılarını ve uygulama adımlarını tanımlar.

------------------------------------------------------------------------

## 6. Translation Cache Sistemi

### Amaç

Aynı metnin tekrar çevrilmesini engelleyerek:

-   API maliyetini azaltmak
-   Çeviri hızını artırmak
-   Çeviri tutarlılığını korumak

------------------------------------------------------------------------

### Mimari Tasarım

Cache sistemi **satır veya paragraf bazlı** çalışır.

Akış:

    Metin al
       ↓
    Hash oluştur
       ↓
    Cache kontrol
       ↓
    Bulundu → Cache kullan
    Bulunamadı → LLM çağrısı
       ↓
    Sonucu cache'e yaz

------------------------------------------------------------------------

### Dosya Yapısı

Önerilen klasör:

    AppData/
       Cache/
          translations/

Her çeviri **hash tabanlı dosya** olarak saklanır.

Örnek:

    c9f1f1f0d8e.json

------------------------------------------------------------------------

### Cache Dosya Formatı

    {
      "original_text": "The Nascent Soul cultivator opened his eyes.",
      "translation": "Ruh Embriyosu gelişimcisi gözlerini açtı.",
      "model": "gemini-2.5-flash",
      "endpoint": "default_gemini",
      "prompt_hash": "ae8391d",
      "created_at": "2026-03-12T22:41:00"
    }

------------------------------------------------------------------------

### Hash Oluşturma

Cache hash şu verilerden oluşturulur:

    original_text
    +
    model_id
    +
    prompt_hash

Örnek:

    sha1(original_text + model_id + prompt_hash)

Sebep:

  Değişken        Neden
  --------------- ------------------
  original_text   metin değişirse
  model           model değişirse
  prompt          prompt değişirse

------------------------------------------------------------------------

### Prompt Hash

Prompt değiştiğinde eski cache kullanılmamalıdır.

    prompt_hash = sha1(prompt_text)

------------------------------------------------------------------------

### Cache Hit Algoritması

Pseudo kod:

    hash = generate_hash(text)

    if cache_exists(hash):
        return cached_translation
    else:
        translation = call_llm()
        save_cache(hash, translation)

------------------------------------------------------------------------

### Cache Boyutu Yönetimi

Cache zamanla büyür.

Önerilen limitler:

    Max Cache Size: 1GB
    veya
    Max Entries: 100000

Temizleme yöntemi:

    LRU (Least Recently Used)

------------------------------------------------------------------------

### Beklenen Kazanç

Gerçek projelerde:

    %20 – %60 API tasarrufu

Özellikle tekrar eden:

-   diyaloglar
-   anlatım kalıpları
-   teknik terimler

cache avantajı sağlar.

------------------------------------------------------------------------

## 7. Terminology Memory Sistemi

### Amaç

Belirli terimlerin **her zaman aynı şekilde çevrilmesini sağlamak.**

Örnek problem:

    Nascent Soul

LLM bazen:

    Ruh Embriyosu

bazen:

    Doğmakta Olan Ruh

şeklinde çevirebilir.

Terminology Memory bunu engeller. Bu doğrultuda Çince ve Korece dillerini de destekleyecek şekilde genişletilebilir.

------------------------------------------------------------------------

### Veri Yapısı

Her proje için ayrı dosya önerilir.

    ProjectConfigs/
       terminology.json

------------------------------------------------------------------------

### Terminology JSON Formatı

    {
      "terms": [
        {
          "source": "Nascent Soul",
          "target": "Ruh Embriyosu"
        },
        {
          "source": "Qi",
          "target": "Qi"
        },
        {
          "source": "Dao",
          "target": "Dao"
        },
        {
          "source": "Spirit Beast",
          "target": "Ruh Canavarı"
        }
      ]
    }

------------------------------------------------------------------------

### Prompt Entegrasyonu

Terminology Memory otomatik olarak prompta eklenir.

Örnek:

    Terminology Rules:

    Nascent Soul → Ruh Embriyosu
    Qi → Qi
    Dao → Dao
    Spirit Beast → Ruh Canavarı

    Use these translations consistently.
    Do not translate them differently.

Bu yöntem LLM davranışını stabilize eder.

------------------------------------------------------------------------

### Ek Özellikler

#### Case Insensitive Destek

Aynı terim şu varyasyonlarda tanınmalıdır:

    nascent soul
    Nascent Soul
    NASCENT SOUL

------------------------------------------------------------------------

#### Regex Destek (Opsiyonel)

Örnek:

    Qi Refinement Stage [0-9]

------------------------------------------------------------------------

#### UI Entegrasyonu

Proje ayarlarında yeni sekme:

    Terminology

UI alanları:

    Source Term → Target Term

Butonlar:

    Add
    Import
    Export
    Delete

------------------------------------------------------------------------

#### Terminology Otomatik Tespit (Opsiyonel)

Prompt Generator sırasında AI şu işlemi yapabilir:

    Extract important terms from the text

Örnek sonuç:

    Nascent Soul
    Qi
    Spirit Beast
    Heavenly Tribulation

Bu terimler kullanıcıya önerilir.

------------------------------------------------------------------------

### Terminology Kullanım Yöntemleri

#### Yöntem 1 (Önerilen)

Terminology kuralları **prompt içine eklenir.**

Avantaj:

-   daha doğal çeviri
-   bağlam korunur

------------------------------------------------------------------------

#### Yöntem 2

Çeviri sonrası otomatik replace.

    text.replace()

Ancak bağlam hatalarına sebep olabilir.

------------------------------------------------------------------------

### Backend Sınıfları

#### TranslationCache

Temel metodlar:

    get(text)
    set(text, translation)
    cleanup()

------------------------------------------------------------------------

#### TerminologyManager

Temel metodlar:

    load_terms()
    add_term()
    remove_term()
    build_prompt_section()

------------------------------------------------------------------------

#### Önerilen Kod Yapısı

    yznvltranslate/

       cache/
          translation_cache.py

       terminology/
          terminology_manager.py

------------------------------------------------------------------------



#### Beklenen Performans Artışı

| Özellik | Kazanç |
|-------|--------------|
| Translation Cache | %20--60 API tasarrufu |
| Terminology Memory | Daha tutarlı çeviri |
| Birlikte kullanım | 2‑3x daha hızlı çeviri |

## 8. Bölüm Düzenleyici - Text Editor
Bölüm düzenleyici, çeviri sonrası düzenleme için kullanılacak. Ana ekrandaki bölüm listesinde yer alan "Orjinal Dosya" ve Çevirilen Dosya" listesinde yer alan dosyalar çift tıklandığında bölüm düzenleyici (text editor) açılacak. Bu düzenleyici, çevirinin düzenlenmesi için kullanılacak. 

### Özellikler

-   Çift tıklandığında bölüm düzenleyici açılacak.
-   Bu düzenleyici, çevirinin düzenlenmesi için kullanılacak.
-   Düzenleme bittikten sonra kaydetme butonu ile yada CTRL+S ile kaydedilecek.
-   Kaydetme işlemi sonrası ana ekrandaki bölüm listesinde yer alan "Çevirilen Dosya" listesindeki dosya güncellenecek.
-   ESC tuşuna basıldığında düzenleyici kapatılacak. Değişiklik varsa kaydetme için uyarı verilecek.
-   Kelime sayısı, karakter sayısı, satır sayısı gibi bilgiler görüntülenecek.
-   Bölümün tekrar çevirisi yapılabilmesi için bölüm olacak. Bu bölümde API ayarı, model ayarı, prompt ayarı, terminology ayarı, cache ayarı gibi ayarlar yapılabilecek. Bu ayarlar sadece o bölüm için geçerli olacak. Çeviri butonuna basıldığında sadece o bölüm için çeviri yapılacak.
#### ESC ile kapatma
ESC veya kapatma:

Eğer değişiklik varsa:
```text
Kaydedilmemiş değişiklik var.

    Kaydet
    Kaydetmeden çık
    İptal
```
**Durum:** Planlama aşamasında

**Versiyon Hedefi:** 2.0.0 (Majör Özellik Güncellemesi)
