import os
import json
import re
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


class LogLocalizationManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LogLocalizationManager, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        if self.initialized:
            return
        self.initialized = True
        self.locales_dir = os.path.join(os.getcwd(), "AppConfigs", "locales")
        os.makedirs(self.locales_dir, exist_ok=True)
        self.current_lang = "tr"
        self.log_data = {}
        self.fallback_log_data = {}
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
        
        # Determine language file
        if self.current_lang == "en":
            lang_filename = "loggeren.json"
        else:
            lang_filename = f"logger_{self.current_lang}.json" if os.path.exists(os.path.join(self.locales_dir, f"logger_{self.current_lang}.json")) else "logger.json"
            
        lang_file = os.path.join(self.locales_dir, lang_filename)
        if not os.path.exists(lang_file) and self.current_lang == "en":
            lang_file = os.path.join(self.locales_dir, "logger_en.json")

        if os.path.exists(lang_file):
            try:
                with open(lang_file, "r", encoding="utf-8") as f:
                    self.log_data = json.load(f)
            except Exception as e:
                print(f"Error loading log translation file {lang_file}: {e}")
                self.log_data = {}
        else:
            self.log_data = {}

        # Always load fallback (logger.json)
        fallback_file = os.path.join(self.locales_dir, "logger.json")
        if os.path.exists(fallback_file):
            try:
                with open(fallback_file, "r", encoding="utf-8") as f:
                    self.fallback_log_data = json.load(f)
            except Exception:
                self.fallback_log_data = {}

    def get_log(self, module_path, line_no=None, default_msg=None, **kwargs):
        """
        Retrieves localized log message.
        If current language is Turkish ('tr') and default_msg is provided,
        returns default_msg directly.
        If current language is English ('en') or other, matches evaluated default_msg against TR template
        and substitutes extracted values into the active language template.
        """
        if default_msg is None:
            return f"[{module_path}:{line_no}]"

        # If current language is Turkish, default_msg evaluated at call site is already Turkish
        if self.current_lang == "tr":
            if kwargs:
                try:
                    return default_msg.format(**kwargs)
                except Exception:
                    return default_msg
            return default_msg

        # For non-Turkish (e.g. English), find active language template and fallback TR template
        en_template = self._find_template(self.log_data, module_path, line_no, default_msg)
        tr_template = self._find_template(self.fallback_log_data, module_path, line_no, default_msg)

        if not en_template:
            return default_msg

        # If kwargs were explicitly passed
        if kwargs:
            try:
                return en_template.format(**kwargs)
            except Exception:
                pass

        # If tr_template and default_msg are available, extract dynamic values from default_msg
        if tr_template:
            try:
                placeholders = re.findall(r'\{([^{}]+)\}', tr_template)
                if not placeholders:
                    return en_template

                parts = re.split(r'\{[^{}]+\}', tr_template)
                escaped_parts = [re.escape(p) for p in parts]
                pattern = '^' + '(.*?)'.join(escaped_parts) + '$'

                match = re.match(pattern, default_msg, re.DOTALL)
                if match and len(match.groups()) == len(placeholders):
                    extracted_vals = match.groups()
                    result = en_template
                    for p_name, val in zip(placeholders, extracted_vals):
                        result = result.replace('{' + p_name + '}', val, 1)
                    return result
            except Exception:
                pass

        return en_template

    def _find_template(self, data_dict, module_path, line_no, default_msg):
        if not data_dict:
            return None
        parts = module_path.split('.')
        current = data_dict
        for p in parts:
            if isinstance(current, dict) and p in current:
                current = current[p]
            else:
                return None
        
        if isinstance(current, list):
            if line_no is not None:
                for item in current:
                    if isinstance(item, dict) and item.get("line") == line_no:
                        return item.get("message")
            if default_msg:
                for item in current:
                    if isinstance(item, dict) and item.get("message") == default_msg:
                        return item.get("message")
            if default_msg:
                for item in current:
                    if isinstance(item, dict) and "message" in item:
                        template = item["message"]
                        try:
                            parts = re.split(r'\{[^{}]+\}', template)
                            escaped_parts = [re.escape(p) for p in parts]
                            pattern = '^' + '(.*?)'.join(escaped_parts) + '$'
                            if re.match(pattern, default_msg, re.DOTALL):
                                return template
                        except Exception:
                            pass
        return None


_loc_mgr = LocalizationManager()
_log_loc_mgr = LogLocalizationManager()


def tr(key, default_val=None):
    return _loc_mgr.tr(key, default_val)


def tr_log(module_path, line_no=None, default_msg=None, **kwargs):
    return _log_loc_mgr.get_log(module_path, line_no=line_no, default_msg=default_msg, **kwargs)


def reload_translations():
    _loc_mgr.load_language()
    _log_loc_mgr.load_language()



