import os
import json

class LocalizationManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LocalizationManager, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        if self.initialized:
            return
        self.initialized = True
        self.locales_dir = os.path.join(os.getcwd(), "AppConfigs", "locales")
        os.makedirs(self.locales_dir, exist_ok=True)
        self.current_lang = "tr"
        self.translations = {}
        self.fallback_translations = {}
        self.load_language()

    def get_current_language(self) -> str:
        settings_file = os.path.join(os.getcwd(), "AppConfigs", "app_settings.json")
        if os.path.exists(settings_file):
            try:
                with open(settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("language", "tr")
            except Exception:
                pass
        return "tr"

    def load_language(self):
        self.current_lang = self.get_current_language()
        
        # Load active language
        lang_file = os.path.join(self.locales_dir, f"{self.current_lang}.json")
        if os.path.exists(lang_file):
            try:
                with open(lang_file, "r", encoding="utf-8") as f:
                    self.translations = json.load(f)
            except Exception as e:
                print(f"Error loading translation file {lang_file}: {e}")
                self.translations = {}
        else:
            self.translations = {}

        # Load fallback (tr) if current language is not tr
        if self.current_lang != "tr":
            fallback_file = os.path.join(self.locales_dir, "tr.json")
            if os.path.exists(fallback_file):
                try:
                    with open(fallback_file, "r", encoding="utf-8") as f:
                        self.fallback_translations = json.load(f)
                except Exception:
                    self.fallback_translations = {}
            else:
                self.fallback_translations = {}
        else:
            self.fallback_translations = {}

    def tr(self, key, default_val=None):
        # Allow dotted paths for nested JSON
        parts = key.split('.')
        
        # Check active language translations
        val = self._get_nested_val(self.translations, parts)
        if val is not None:
            return val
            
        # Check fallback translations
        val = self._get_nested_val(self.fallback_translations, parts)
        if val is not None:
            return val
            
        return default_val if default_val is not None else key

    def _get_nested_val(self, d, parts):
        current = d
        for p in parts:
            if isinstance(current, dict) and p in current:
                current = current[p]
            else:
                return None
        return current

_loc_mgr = LocalizationManager()

def tr(key, default_val=None):
    return _loc_mgr.tr(key, default_val)

def reload_translations():
    _loc_mgr.load_language()
