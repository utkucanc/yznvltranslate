import os
import json
import datetime
from logger import app_logger

class RequestCounterManager:
    """Yapay zeka API istek sayısını takip eden sınıf."""
    def __init__(self, config_folder="AppConfigs"):
        self.config_folder = os.path.join(os.getcwd(), config_folder)
        os.makedirs(self.config_folder, exist_ok=True)
        self.count_file = os.path.join(self.config_folder, "request_count.json")
        self.count = 0
        self.last_date = str(datetime.date.today())
        self.last_model = ""
        self.last_api_key_name = ""
        self._load()

    def _load(self):
        if os.path.exists(self.count_file):
            try:
                with open(self.count_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.count = data.get("count", 0)
                    self.last_date = data.get("last_date", str(datetime.date.today()))
                    self.last_model = data.get("last_model", "")
                    self.last_api_key_name = data.get("last_api_key_name", "")
            except Exception as e:
                app_logger.error(f"Request count yüklenemedi: {e}")
        self._check_reset(self.last_model, self.last_api_key_name)

    def _save(self):
        data = {
            "count": self.count,
            "last_date": self.last_date,
            "last_model": self.last_model,
            "last_api_key_name": self.last_api_key_name
        }
        try:
            with open(self.count_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            app_logger.error(f"Request count kaydedilemedi: {e}")

    def _check_reset(self, current_model, current_api_key_name):
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
            if current_model: self.last_model = current_model
            if current_api_key_name: self.last_api_key_name = current_api_key_name
            self._save()

    def get_count(self, current_model, current_api_key_name):
        self._check_reset(current_model, current_api_key_name)
        return self.count

    def increment(self, current_model, current_api_key_name):
        self._check_reset(current_model, current_api_key_name)
        self.count += 1
        self.last_model = current_model
        self.last_api_key_name = current_api_key_name
        self._save()
        return self.count
