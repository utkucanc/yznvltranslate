import google.generativeai as genai
import os
import json 
import time
from logger import app_logger

TOKEN_DATA_FILENAME = "token_data.json" 

def count_tokens_in_text(text, api_key, model_version="gemini-2.5-flash-preview-09-2025"):
    """
    Verilen metnin kaç token olduğunu Gemini API'si ile hesaplar.
    """
    if not api_key:
        return None, "API Anahtarı sağlanmadı."

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_version) 
        
        # Kota aşımı durumları için ufak bir retry mekanizması
        max_retries = 3
        for attempt in range(max_retries):
            try:
                app_logger.debug(f"Gemini API istek atılıyor (Deneme {attempt+1}/{max_retries})...")
                response = model.count_tokens(text)
                time.sleep(1) # API limitlerine takılmamak için her istek arası biraz bekle
                app_logger.debug(f"Gemini API isteği başarılı. Token Sayısı: {response.total_tokens}")
                return response.total_tokens, None
            except Exception as inner_e:
                app_logger.warning(f"Gemini API Çağrısında hata (Deneme {attempt+1}/{max_retries}): {inner_e}")
                if "429" in str(inner_e) or "ResourceExhausted" in str(inner_e):
                    if attempt < max_retries - 1:
                        app_logger.info("Kota aşıldı belirtisi, 3 saniye bekleniyor...")
                        time.sleep(3) # Kota aşıldıysa 3 saniye bekle ve tekrar dene
                        continue
                    else:
                        app_logger.error("API Kota Sınırı Aşıldı.")
                        return None, "API Kota Sınırı Aşıldı. Lütfen bir süre sonra tekrar deneyin."
                raise inner_e # Diğer hataları dışarı yolla
                
    except Exception as e:
        app_logger.error(f"Token sayımı genel hatası: {str(e)}")
        return None, f"Token sayımı hatası: {str(e)}"

def count_tokens_in_file(file_path, api_key, model_version="gemini-2.5-flash-preview-09-2025"):
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
    
    return count_tokens_in_text(file_content, api_key, model_version)


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
        print(f"Hata: Token kaydetme başarısız: {e}")