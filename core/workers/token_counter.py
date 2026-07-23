import os
import json
import time
from logger import app_logger

TOKEN_DATA_FILENAME = "token_data.json"
import re

def estimate_tokens(text):
    """
    HTTP isteği gerektirmeyen, script-aware token tahmini.
    Asya dilleri (CJK) ve Latin/Kiril karışık metinlerde
    tek-oranlı tahminlerden daha isabetlidir.
    """
    if not text:
        return 0

    # CJK (Çince, Japonca Kanji, Korece Hanja) - genelde karakter başına ~1-1.5 token
    cjk_pattern = re.compile(
        r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff'  # CJK Unified + Ext A + Compatibility
        r'\u3040-\u309f\u30a0-\u30ff'                  # Hiragana, Katakana
        r'\uac00-\ud7af]'                              # Hangul Syllables
    )
    cjk_chars = cjk_pattern.findall(text)
    cjk_count = len(cjk_chars)

    # CJK karakterleri çıkarılmış geri kalan metin (Latin, Kiril, rakam, noktalama, boşluk)
    remaining_text = cjk_pattern.sub('', text)

    # Kelime/whitespace-bazlı parçalar (Latin script için)
    # Ortalama İngilizce/Türkçe: ~4 karakter = 1 token
    non_cjk_token_estimate = len(remaining_text) / 4.0

    # CJK: her karakter neredeyse kendi başına bir token'a yakındır,
    # biraz daha düşük bir katsayı (1.0-1.5 arası) gerçekçi sonuç verir
    cjk_token_estimate = cjk_count * 1.4

    total = non_cjk_token_estimate + cjk_token_estimate
    return int(round(total))

def get_local_token_count_approx(text):
    """
    Hızlı ve yerel token hesaplaması (Transformers AutoTokenizer ile).
    Eğer kütüphane eksikse veya model yüklenmezse kabaca karakter sayısına göre tahmin yapar.
    """
    if not text:
        return 0

    # CJK (Çince, Japonca Kanji, Korece Hanja) - genelde karakter başına ~1-1.5 token
    cjk_pattern = re.compile(
        r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff'  # CJK Unified + Ext A + Compatibility
        r'\u3040-\u309f\u30a0-\u30ff'                  # Hiragana, Katakana
        r'\uac00-\ud7af]'                              # Hangul Syllables
    )
    cjk_chars = cjk_pattern.findall(text)
    cjk_count = len(cjk_chars)

    # CJK karakterleri çıkarılmış geri kalan metin (Latin, Kiril, rakam, noktalama, boşluk)
    remaining_text = cjk_pattern.sub('', text)

    # Kelime/whitespace-bazlı parçalar (Latin script için)
    # Ortalama İngilizce/Türkçe: ~4 karakter = 1 token
    non_cjk_token_estimate = len(remaining_text) / 4.0

    # CJK: her karakter neredeyse kendi başına bir token'a yakındır,
    # biraz daha düşük bir katsayı (1.0-1.5 arası) gerçekçi sonuç verir
    cjk_token_estimate = cjk_count * 1.4

    total = non_cjk_token_estimate + cjk_token_estimate
    return int(round(total))

def count_tokens_in_text(text, api_key=None, model_version="gemini-2.5-flash",
                         endpoint_id=None, endpoint_config=None):
    """
    Verilen metnin kaç token olduğunu hesaplar.
    MCP entegrasyonu: LLMProvider üzerinden Gemini veya OpenAI-uyumlu servislerle çalışır.
    """
    try:
        from core.llm_provider import LLMProvider

        # Provider oluştur
        if endpoint_config:
            provider = LLMProvider(endpoint=endpoint_config, api_key=api_key)
        elif endpoint_id:
            provider = LLMProvider(endpoint_id=endpoint_id)
        elif api_key:
            provider = LLMProvider(
                endpoint={
                    "id": "legacy_gemini",
                    "name": "Eski Gemini",
                    "type": "gemini",
                    "model_id": model_version,
                    "base_url": None,
                    "use_key_rotation": False,
                    "headers": {}
                },
                api_key=api_key
            )
        else:
            return None, "API Anahtarı veya endpoint sağlanmadı."

        # Kota aşımı durumları için retry
        max_retries = 3
        for attempt in range(max_retries):
            try:
                app_logger.debug(f"Token sayım isteği (Deneme {attempt+1}/{max_retries})...")
                token_count = provider.count_tokens(text)
                time.sleep(1)
                app_logger.debug(f"Token sayımı başarılı: {token_count}")
                return token_count, None
            except Exception as inner_e:
                app_logger.warning(f"Token sayım hatası (Deneme {attempt+1}/{max_retries}): {inner_e}")
                if ("429" in str(inner_e) or "ResourceExhausted" in str(inner_e)):
                    if attempt < max_retries - 1:
                        app_logger.info("Kota aşıldı, 3 saniye bekleniyor...")
                        time.sleep(3)
                        continue
                    else:
                        return None, "API Kota Sınırı Aşıldı."
                raise inner_e

    except ImportError:
        # llm_provider yüklenemezse eski yönteme geri dön
        app_logger.warning("llm_provider yüklenemedi, eski Gemini yöntemine dönülüyor.")
        return _legacy_count_tokens(text, api_key, model_version)
    except Exception as e:
        app_logger.error(f"Token sayımı genel hatası: {str(e)}")
        return None, f"Token sayımı hatası: {str(e)}"

#############
def _legacy_count_tokens(text, api_key, model_version):
    """Eski Gemini API ile token sayımı (geriye uyumluluk)."""
    if not api_key:
        return None, "API Anahtarı sağlanmadı."
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.count_tokens(
            model=model_version,
            contents=text
        )
        time.sleep(1)
        return response.total_tokens, None
    except Exception as e:
        return None, f"Token sayımı hatası: {str(e)}"


def count_tokens_in_file(file_path, api_key=None, model_version="gemini-2.5-flash",
                         endpoint_id=None, endpoint_config=None):
    """
    Belirtilen TXT dosyasındaki metnin kaç token olduğunu hesaplar.
    """
    if not os.path.exists(file_path):
        return None, f"Dosya bulunamadı: '{file_path}'."

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
    except Exception as e:
        return None, f"Dosya okunurken hata: {str(e)}"

    return count_tokens_in_text(file_content, api_key, model_version,
                                endpoint_id=endpoint_id, endpoint_config=endpoint_config)


def load_token_data(config_folder_path):
    token_data_path = os.path.join(config_folder_path, TOKEN_DATA_FILENAME)
    if os.path.exists(token_data_path):
        try:
            with open(token_data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"file_token_data": {}, "total_original_tokens": 0, "total_translated_tokens": 0, "total_combined_tokens": 0}
    return {"file_token_data": {}, "total_original_tokens": 0, "total_translated_tokens": 0, "total_combined_tokens": 0}


def save_token_data(config_folder_path, data):
    token_data_path = os.path.join(config_folder_path, TOKEN_DATA_FILENAME)
    try:
        os.makedirs(config_folder_path, exist_ok=True)
        with open(token_data_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        app_logger.error(f"Hata: Token kaydetme başarısız: {e}")