import os
import re

def temizle_ve_kaydet(dosya_adi: str) -> tuple[bool, str]:
    """
    Belirtilen TXT dosyasının içeriğini temizler ve aynı dosyaya kaydeder.
    
    Dosyanın içeriğindeki ilk "**Bölüm**" veya "**Bölüm X**" (X bir sayı olabilir)
    başlığından önceki tüm metni siler. Eğer bir bölüm başlığı bulunamazsa,
    dosyayı olduğu gibi bırakır.

    Args:
        dosya_adi (str): Temizlenecek TXT dosyasının tam yolu.

    Returns:
        tuple[bool, str]: İşlem başarılıysa (True, "Bölüm Başlığı") veya (False, "Hata Mesajı").
    """
    try:
        if not os.path.exists(dosya_adi):
            return False, f"Hata: '{dosya_adi}' dosyası bulunamadı."

        with open(dosya_adi, 'r', encoding='utf-8') as dosya:
            icerik = dosya.read()
        
        # Tüm bölüm formatlarını algılayan güncellenmiş regex
        # Örnekler: **Bölüm**, **1. Bölüm**, **Bölüm:1**, **Bölüm 1**, **1.Bölüm**
        bolum_baslangici = re.search(r'\*\*(\d+\.\s*)?Bölüm[\s:]*\d*[\s:]*\*\*|'
                                    r'\*\*Bölüm[\s:]*\**', 
                                    icerik, re.IGNORECASE) # ignorecase ekleyerek büyük/küçük harf duyarsız yapıldı
        
        if bolum_baslangici:
            # Bölüm başlangıcından itibaren içeriği al
            temiz_icerik = icerik[bolum_baslangici.start():]
            
            # Dosyayı temizlenmiş içerikle yeniden yaz
            with open(dosya_adi, 'w', encoding='utf-8') as dosya:
                dosya.write(temiz_icerik)
            
            return True, bolum_baslangici.group().strip()
        else:
            return False, "Bölüm başlığı bulunamadı. Dosya temizlenmedi."
    
    except Exception as e:
        return False, f"Temizleme sırasında hata: {str(e)}"

if __name__ == "__main__":
    # Bu kısmı test amaçlı kullanabiliriz
    # Örnek bir dosya oluştur
    test_file_name = "test_temizlik.txt"
    with open(test_file_name, 'w', encoding='utf-8') as f:
        f.write("Gereksiz giriş metni.\n\n")
        f.write("Bu kısım silinmeli miydi?\n")
        f.write("**Bölüm 1:** Buradan sonrası kalmalı.\n")
        f.write("Bu da bölümün bir parçası.\n")
    
    print(f"'{test_file_name}' temizleniyor...")
    basarili, mesaj = temizle_ve_kaydet(test_file_name)
    if basarili:
        print(f"✓ '{test_file_name}': Başarılı. Bölüm başlığı: {mesaj}")
        with open(test_file_name, 'r', encoding='utf-8') as f:
            print("\nTemizlenmiş içerik:")
            print(f.read())
    else:
        print(f"✗ '{test_file_name}': Hata/Uyarı: {mesaj}")

    # Olmayan bir dosyayı deneme
    print("\nOlmayan bir dosyayı deneme:")
    basarili, mesaj = temizle_ve_kaydet("olmayan_dosya.txt")
    print(f"✗ olmayan_dosya.txt: {mesaj}")

    # Sadece bölüm başlığı olmayan bir dosya denemesi
    print("\nBölüm başlığı olmayan bir dosyayı deneme:")
    test_file_no_chapter = "test_no_chapter.txt"
    with open(test_file_no_chapter, 'w', encoding='utf-8') as f:
        f.write("Bu dosyada bölüm başlığı yok.\n")
        f.write("Tamamen silinmemeli, olduğu gibi kalmalı.\n")
    basarili, mesaj = temizle_ve_kaydet(test_file_no_chapter)
    if basarili:
        print(f"✓ '{test_file_no_chapter}': Başarılı. Bölüm başlığı: {mesaj}")
    else:
        print(f"✗ '{test_file_no_chapter}': Hata/Uyarı: {mesaj}")
    os.remove(test_file_name)
    os.remove(test_file_no_chapter)
