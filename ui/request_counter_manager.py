"""
RequestCounterManager — Yapay Zeka API istek sayısını izleme sistemi.

V2.1.0 İyileştirmeleri:
  - Her API endpoint / model için ayrı günlük kayıt
  - get_daily_stats() ile geçmiş istatistiklere erişim
  - Geriye uyumluluk: eski get_count() / increment() API'leri korunuyor

Veri Formatı (request_stats.json):
{
  "2026-04-03": {
    "GeminiModel-gemini-flash": 15,
    "OpenRouter-mixtral": 8
  },
  "2026-04-04": { ... }
}
"""

import os
import json
import datetime
from logger import app_logger


class RequestCounterManager:
    """Yapay zeka API istek sayısını endpoint/model bazında günlük takip eden sınıf."""

    def __init__(self, config_folder="AppConfigs"):
        self.config_folder = os.path.join(os.getcwd(), config_folder)
        os.makedirs(self.config_folder, exist_ok=True)

        # Yeni detaylı istatistik dosyası
        self.stats_file = os.path.join(self.config_folder, "request_stats.json")
        # Eski uyumluluk dosyası (geriye uyumluluk için korunuyor)
        self.count_file = os.path.join(self.config_folder, "request_count.json")

        self._stats: dict = {}  # {"tarih": {"api_key": count}}
        self._load_stats()

        # Geriye uyumluluk için basit sayaç
        self.count = 0
        self.last_date = str(datetime.date.today())
        self.last_model = ""
        self.last_api_key_name = ""
        self._load_legacy()

    # --------------- Yeni Çok-API İstatistik Sistemi ---------------

    def _load_stats(self):
        """Detaylı istatistikleri yükler."""
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, "r", encoding="utf-8") as f:
                    self._stats = json.load(f)
            except Exception as e:
                app_logger.error(f"request_stats.json yüklenemedi: {e}")
                self._stats = {}

    def _save_stats(self):
        """Detaylı istatistikleri kaydeder."""
        try:
            with open(self.stats_file, "w", encoding="utf-8") as f:
                json.dump(self._stats, f, indent=2, ensure_ascii=False)
        except Exception as e:
            app_logger.error(f"request_stats.json kaydedilemedi: {e}")

    def record_request(self, model: str = "", api_key_name: str = ""):
        """
        API isteğini tarih + endpoint anahtarıyla kaydeder.
        
        Args:
            model: Model adı (örn: 'gemini-2.5-flash')
            api_key_name: API anahtarı adı veya endpoint adı
        """
        today = str(datetime.date.today())
        # Anahtar: "model-apiname" veya sadece model
        key = f"{model}-{api_key_name}" if api_key_name else (model or "unknown")
        
        if today not in self._stats:
            self._stats[today] = {}
        
        self._stats[today][key] = self._stats[today].get(key, 0) + 1
        self._save_stats()
        app_logger.debug(f"API isteği kaydedildi: {today}/{key} = {self._stats[today][key]}")

    def get_daily_stats(self) -> dict:
        """Tüm geçmiş günlerin istatistiklerini döndürür."""
        return dict(self._stats)

    def get_today_stats(self) -> dict:
        """Bugünkü API istek sayılarını döndürür."""
        today = str(datetime.date.today())
        return self._stats.get(today, {})

    def get_total_today(self) -> int:
        """Bugünkü toplam istek sayısını döndürür."""
        return sum(self.get_today_stats().values())

    def get_stats_for_days(self, days: int = 7) -> dict:
        """Son N günün istatistiklerini döndürür."""
        result = {}
        today = datetime.date.today()
        for i in range(days):
            day = str(today - datetime.timedelta(days=i))
            if day in self._stats:
                result[day] = self._stats[day]
        return result

    # --------------- Geriye Uyumluluk (Eski API) ---------------

    def _load_legacy(self):
        """Eski request_count.json'dan yükler (geriye uyumluluk)."""
        if os.path.exists(self.count_file):
            try:
                with open(self.count_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.count = data.get("count", 0)
                self.last_date = data.get("last_date", str(datetime.date.today()))
                self.last_model = data.get("last_model", "")
                self.last_api_key_name = data.get("last_api_key_name", "")
            except Exception as e:
                app_logger.error(f"request_count.json yüklenemedi: {e}")
        self._check_reset_legacy(self.last_model, self.last_api_key_name)

    def _save_legacy(self):
        data = {
            "count": self.count,
            "last_date": self.last_date,
            "last_model": self.last_model,
            "last_api_key_name": self.last_api_key_name,
        }
        try:
            with open(self.count_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            app_logger.error(f"request_count.json kaydedilemedi: {e}")

    def _check_reset_legacy(self, current_model, current_api_key_name):
        today = str(datetime.date.today())
        should_reset = False
        if today != self.last_date:
            should_reset = True
        elif current_model and current_model != self.last_model:
            should_reset = True
        elif current_api_key_name and current_api_key_name != self.last_api_key_name:
            should_reset = True

        if should_reset:
            self.count = 0
            self.last_date = today
            if current_model:
                self.last_model = current_model
            if current_api_key_name:
                self.last_api_key_name = current_api_key_name
            self._save_legacy()

    def get_count(self, current_model, current_api_key_name):
        """Geriye uyumluluk — günlük istek sayısını döndürür."""
        self._check_reset_legacy(current_model, current_api_key_name)
        return self.count

    def increment(self, current_model, current_api_key_name):
        """Geriye uyumluluk — sayacı artırır ve yeni sisteme de kaydeder."""
        self._check_reset_legacy(current_model, current_api_key_name)
        self.count += 1
        self.last_model = current_model
        self.last_api_key_name = current_api_key_name
        self._save_legacy()
        # Yeni sisteme de kaydet
        self.record_request(current_model, current_api_key_name)
        return self.count
