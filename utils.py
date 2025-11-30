import re
import os
import datetime

def format_file_size(size_bytes: int) -> str:
    """Dosya boyutunu okunabilir formata dönüştürür."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

def natural_sort_key(s):
    """Metinleri doğal (insan dostu) sıraya göre sıralamak için bir anahtar döndürür."""
    # Sayıları alfanümerik olarak değil, sayısal olarak sıralar
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split(r'(\d+)', s)]

def log_error(message):
    """
    Hata mesajını 'Logs' klasörüne 'eLog-Tarih-Saat.txt' formatında kaydeder.
    """
    try:
        # Programın çalıştığı dizinde Logs klasörü yolu
        log_folder = os.path.join(os.getcwd(), "Logs")
        
        # Klasör yoksa oluştur
        if not os.path.exists(log_folder):
            os.makedirs(log_folder)

        # Dosya adı için zaman damgası: Yıl-Ay-Gün-Saat-Dakika-Saniye
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        filename = f"eLog-{timestamp}.txt"
        filepath = os.path.join(log_folder, filename)

        # Hatayı dosyaya yaz
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"Zaman: {datetime.datetime.now()}\n")
            f.write("-" * 30 + "\n")
            f.write(str(message))
            f.write("\n" + "-" * 30 + "\n")
            
    except Exception as e:
        # Loglama sırasında hata olursa (örn: yetki hatası), bunu sessizce yutmak 
        # veya konsola yazdırmak gerekir ki sonsuz döngü olmasın.
        print(f"Loglama hatası: {e}")

if __name__ == "__main__":
    # Test fonksiyonları
    print("Dosya Boyutu Testleri:")
    print(f"100 B: {format_file_size(100)}")
    
    # Log test
    log_error("Bu bir test hata mesajıdır.")
    print("Test logu oluşturuldu.")