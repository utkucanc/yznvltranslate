import re
import os

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

if __name__ == "__main__":
    # Test fonksiyonları
    print("Dosya Boyutu Testleri:")
    print(f"100 B: {format_file_size(100)}")
    print(f"1024 B: {format_file_size(1024)}")
    print(f"1500 B: {format_file_size(1500)}")
    print(f"1048576 B: {format_file_size(1048576)}") # 1 MB
    
    print("\nDoğal Sıralama Testleri:")
    files = ["page_1.txt", "page_10.txt", "page_2.txt", "chapter_A.txt", "chapter_B.txt"]
    sorted_files = sorted(files, key=natural_sort_key)
    print(f"Orijinal: {files}")
    print(f"Sıralı: {sorted_files}")

    # Örnek dosya yolları ile deneme
    file_paths_test = [os.path.join("path", "to", "file10.txt"), os.path.join("path", "to", "file2.txt")]
    sorted_paths = sorted(file_paths_test, key=lambda x: natural_sort_key(os.path.basename(x)))
    print(f"Yol sıralama testi: {sorted_paths}")
