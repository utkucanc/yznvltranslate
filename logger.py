import logging
import os
import sys

def setup_logger(log_folder="AppConfigs", log_file="app.log"):
    """
    Uygulama genelinde kullanılacak merkezi log yapılandırmasını kurar.
    Logs klasörü yoksa oluşturur. Dosyaya ve konsola çıktı verir.
    """
    # Klasör yoksa oluştur
    if not os.path.exists(log_folder):
        try:
            os.makedirs(log_folder)
        except Exception as e:
            print(f"Log klasörü oluşturulamadı: {e}")
            return logging.getLogger("AppFallbackLogger")

    log_path = os.path.join(log_folder, log_file)

    # Logger kök (root) örneğini al
    logger = logging.getLogger("AppLogger")
    
    # Hali hazırda handler varsa tekrar ekleme (çoklanmayı önlemek için)
    if not logger.handlers:
        logger.setLevel(logging.DEBUG) # En düşük seviyede dinle

        # Dosyaya yazılacak format (detaylı)
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
        
        # Konsola yazdırılacak format (daha sade)
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')

        # Dosya Handler (AppConfigs/app.log dosyasına yazar)
        file_handler = logging.FileHandler(log_path, mode='a', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)

        # Konsol Handler (Cmd/Terminal ekranına yazar)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger

# Global bir logger objesi oluşturuyoruz ki diğer dosyalardan kolayca erişilsin
app_logger = setup_logger()

# Yakalanmayan (Unhandled) hataların programa sessizce çökertmesi yerine loga yazılmasını sağlar
def global_exception_handler(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    app_logger.critical("Yakalanmayan İstisna (Crash):", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = global_exception_handler
