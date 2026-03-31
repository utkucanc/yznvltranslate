import os

def cince_karakter_say(metin):
    """
    Bir metindeki Çince karakterlerin (CJK Unified Ideographs) sayısını döndürür.
    """
    sayac = 0
    for karakter in metin:
        # Standart Çince karakter Unicode aralığı: 4E00 - 9FFF
        if ('\uac00' <= karakter <= '\ud7a3') or \
           ('\u1100' <= karakter <= '\u11ff') or \
           ('\u3130' <= karakter <= '\u318f'):
            sayac += 1
    if sayac > 100:
        return sayac
    else:
        sayac = 0
        return sayac

def klasoru_tara(klasor_yolu):
    """
    Belirtilen klasördeki txt dosyalarını bulur ve Çince karakter sayılarını raporlar.
    """
    if not os.path.exists(klasor_yolu):
        print(f"Hata: '{klasor_yolu}' yolu bulunamadı.")
        return

    print(f"--- '{klasor_yolu}' klasörü taranıyor ---\n")
    silinecek_list = []
    toplam_dosya = 0
    sorunsuz_dosya = 0
    sorunlu_dosya = 0
    for dosya_adi in os.listdir(klasor_yolu):
        if dosya_adi.endswith(".txt"):
            dosya_yolu = os.path.join(klasor_yolu, dosya_adi)
            dosya_tam_yolu = os.path.abspath(dosya_yolu)
            toplam_dosya += 1
            
            try:
                # Dosyayı okuma (Genellikle utf-8 kullanılır, hata verirse 'ignore' ile geçilir)
                with open(dosya_yolu, 'r', encoding='utf-8', errors='ignore') as f:
                    icerik = f.read()
                    sayi = cince_karakter_say(icerik)
                    if sayi > 1000:
                        #print(dosya_tam_yolu)
                        #print(dosya_yolu)
                        print(f"Dosya: {dosya_adi} -> Çince Karakter Sayısı: {sayi}")
                        print(f"Dosya: {dosya_adi} -> Silindi")
                        sorunlu_dosya += 1
#                        os.remove(dosya_tam_yolu)
                        silinecek_list.append(dosya_tam_yolu)
                        
                        
                        
                    if 0 <sayi <1000:
                        print(f"Dosya: {dosya_adi} -> Çince Karakter Sayısı: {sayi}")
                    else:
                        sorunsuz_dosya += 1
                    
            except Exception as e:
                print(f"Hata: {dosya_adi} okunamadı. Sebebi: {e}")
    
    if toplam_dosya == 0:
        print("Klasörde hiç .txt dosyası bulunamadı.")
    else:
        print(f"Sorunlu Dosya Sayısı {sorunlu_dosya} .")
        print(f"Sorunsuz Dosya Sayısı {sorunsuz_dosya} .")
        print(f"Toplam Dosya Sayısı {toplam_dosya} .")
    return silinecek_list

def dosya_sil(dosya_list):
    say = 0
    for dosya_yol in dosya_list:
        os.remove(dosya_list[say])
        say = say + 1
    print("Silme Tamamlandı")
# --- KULLANIM ---
# Aşağıdaki yolu kendi klasör yolunuzla değiştirin.
# Windows örneği: r"C:\Kullanicilar\Belgelerim\Dosyalar"
# Mac/Linux örneği: "/home/user/dosyalar"

hedef_klasor = "./trslt"  # Buraya kendi klasör yolunuzu yazın
dosya_sil(klasoru_tara(hedef_klasor))