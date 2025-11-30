import google.generativeai as genai
import os
import json # JSON işlemleri için eklendi
import time # Dosya değiştirme zamanları için eklendi

TOKEN_DATA_FILENAME = "token_data.json" # Token verilerinin kaydedileceği dosya adı

def count_tokens_in_text(text, api_key):
    """
    Verilen metnin kaç token olduğunu Gemini API'si ile hesaplar.
    """
    if not api_key:
        return None, "API Anahtarı sağlanmadı."

    try:
        genai.configure(api_key=api_key)
        # Token sayımı için genellikle daha hafif ve kararlı bir model seçilir.
        model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20') 
        response = model.count_tokens(text)
        return response.total_tokens, None
    except Exception as e:
        # API ile iletişimde veya token sayımında bir hata oluştuğunda
        return None, f"Token sayımı sırasında API hatası veya geçersiz metin: {str(e)}"

def count_tokens_in_file(file_path, api_key):
    """
    Belirtilen TXT dosyasındaki metnin kaç token olduğunu Gemini API'si ile hesaplar.
    Bu fonksiyon, dosya içeriğini okur ve ardından count_tokens_in_text fonksiyonunu çağırır.
    """
    if not os.path.exists(file_path):
        return None, f"Dosya bulunamadı: '{file_path}'."

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
    except Exception as e:
        return None, f"Dosya okunurken hata: {str(e)}"
    
    return count_tokens_in_text(file_content, api_key)


def load_token_data(config_folder_path):
    """
    Belirtilen config klasöründen token sayım verilerini yükler.
    Dosya bulunamazsa veya okunurken hata oluşursa boş bir veri yapısı döndürür.
    """
    token_data_path = os.path.join(config_folder_path, TOKEN_DATA_FILENAME)
    if os.path.exists(token_data_path):
        try:
            with open(token_data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError, Exception) as e:
            # Hata durumunda boş bir yapı döndür ve uyarı mesajı bas
            print(f"Uyarı: '{token_data_path}' dosyasından token verileri yüklenirken hata oluştu. Yeni bir veri yapısı oluşturuluyor: {e}")
            return {"file_token_data": {}, "total_original_tokens": 0, "total_translated_tokens": 0, "total_combined_tokens": 0}
    # Dosya yoksa veya ilk kez yükleniyorsa boş bir yapı döndür
    return {"file_token_data": {}, "total_original_tokens": 0, "total_translated_tokens": 0, "total_combined_tokens": 0}

def save_token_data(config_folder_path, data):
    """
    Token sayım verilerini belirtilen config klasörüne kaydeder.
    Kaydetmeden önce klasörün var olduğundan emin olur.
    """
    token_data_path = os.path.join(config_folder_path, TOKEN_DATA_FILENAME)
    try:
        # Klasörün var olduğundan emin ol, yoksa oluştur
        os.makedirs(config_folder_path, exist_ok=True)
        with open(token_data_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Hata: '{token_data_path}' dosyasına token verileri kaydedilirken: {e}")
