import logging
import os
import sys
import json
from logging.handlers import RotatingFileHandler


def set_app_log_level(level_input):
    """
    Uygulamanın log seviyesini dinamik olarak ayarlar.
    Hiyerarşi: DEBUG (10) < INFO (20) < WARNING (30) < ERROR (40)
    Seçilen seviyenin altındaki log mesajları süzülür (gösterilmez).
    """
    if isinstance(level_input, str):
        level = getattr(logging, str(level_input).upper(), logging.INFO)
    else:
        level = level_input

    logger = logging.getLogger("AppLogger")
    logger.setLevel(level)
    for h in logger.handlers:
        h.setLevel(level)


def _load_initial_log_level(log_folder="AppConfigs"):
    settings_file = os.path.join(log_folder, "app_settings.json")
    if os.path.exists(settings_file):
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("log_level", "INFO")
        except Exception:
            pass
    return "INFO"


def setup_logger(log_folder="AppConfigs", log_file="app.log"):
    """
    Uygulama genelinde kullanılacak merkezi log yapılandırmasını kurar.
    Logs klasörü yoksa oluşturur. Dosyaya (RotatingFileHandler) ve konsola çıktı verir.
    Log dosyası max 5MB, en fazla 3 yedek tutar.
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
        initial_log_level_str = _load_initial_log_level(log_folder)
        initial_level = getattr(logging, initial_log_level_str.upper(), logging.INFO)

        logger.setLevel(initial_level)

        # Dosyaya yazılacak format (detaylı)
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
        
        # Konsola yazdırılacak format (daha sade)
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')

        # Rotating Dosya Handler: max 5MB, 3 yedek (app.log, app.log.1, app.log.2, app.log.3)
        file_handler = RotatingFileHandler(
            log_path,
            mode='a',
            encoding='utf-8',
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=3
        )
        file_handler.setLevel(initial_level)
        file_handler.setFormatter(file_formatter)

        # Konsol Handler (Cmd/Terminal ekranına yazar)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(initial_level)
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
