import google.generativeai as genai
import os
import json 
import time

TOKEN_DATA_FILENAME = "token_data.json" 

def count_tokens_in_text(text, api_key, model_version="gemini-2.5-flash-preview-09-2025"):
    """
    Verilen metnin kaç token olduğunu Gemini API'si ile hesaplar.
    """
    if not api_key:
        return None, "API Anahtarı sağlanmadı."

    try:
        genai.configure(api_key=api_key)
        # Seçili model versiyonunu kullan
        model = genai.GenerativeModel(model_version) 
        response = model.count_tokens(text)
        return response.total_tokens, None
    except Exception as e:
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