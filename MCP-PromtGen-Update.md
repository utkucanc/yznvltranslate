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

#### C. Kayıt ve Kullanım
Oluşturulan promt otomatik olarak **`ProjeAdı-PromtGen.txt`** adıyla kaydedilir ve proje ayarlarında seçilebilir hale gelir.

### Arayüz (UI) Entegrasyonu
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
**Durum:** Planlama aşamasında
**Versiyon Hedefi:** 2.0.0 (Majör Özellik Güncellemesi)
