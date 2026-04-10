"""
LLM Provider — Farklı yapay zeka servislerine bağlanabilme altyapısı.

Desteklenen türler:
  - gemini: Google Generative AI (google.generativeai)
  - openai_compatible: OpenAI, OpenRouter, Anthropic, DeepSeek, Groq, TogetherAI, vLLM, Ollama, LM Studio, LocalAI
"""

import os
import json
import random
import hashlib
import time
from logger import app_logger

# ─────────────────────────── Sabitler ───────────────────────────

MCP_ENDPOINTS_FILE = os.path.join(os.getcwd(), "AppConfigs", "MCP_Endpoints.json")
MCP_KEYS_FOLDER = os.path.join(os.getcwd(), "AppConfigs", "APIKeys", "MCP")

DEFAULT_ENDPOINTS = {
    "active_endpoint_id": "default_gemini",
    "endpoints": [
        {
            "id": "default_gemini",
            "name": "Standart Gemini",
            "type": "gemini",
            "model_id": "gemini-2.5-flash",
            "base_url": None,
            "use_key_rotation": True,
            "headers": {}
        }
    ]
}

# ─────────────────────── Yardımcı Fonksiyonlar ───────────────────────


def load_endpoints() -> dict:
    """MCP_Endpoints.json dosyasını okur.  Yoksa varsayılan döndürür."""
    if os.path.exists(MCP_ENDPOINTS_FILE):
        try:
            with open(MCP_ENDPOINTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            app_logger.error(f"MCP_Endpoints.json okunamadı: {e}")
    return DEFAULT_ENDPOINTS.copy()


def save_endpoints(data: dict):
    """MCP_Endpoints.json dosyasına yazar."""
    os.makedirs(os.path.dirname(MCP_ENDPOINTS_FILE), exist_ok=True)
    with open(MCP_ENDPOINTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_endpoint_by_id(endpoint_id: str) -> dict | None:
    """Belirli bir endpoint'i ID ile bulur."""
    data = load_endpoints()
    for ep in data.get("endpoints", []):
        if ep["id"] == endpoint_id:
            return ep
    return None


def get_active_endpoint() -> dict | None:
    """Aktif endpoint'i döndürür."""
    data = load_endpoints()
    active_id = data.get("active_endpoint_id")
    if active_id:
        return get_endpoint_by_id(active_id)
    endpoints = data.get("endpoints", [])
    return endpoints[0] if endpoints else None


def load_api_keys(endpoint_id: str) -> list[str]:
    """Belirtilen endpoint ID'ye ait API anahtarlarını dosyadan okur."""
    key_file = os.path.join(MCP_KEYS_FOLDER, f"{endpoint_id}.txt")
    keys = []
    if os.path.exists(key_file):
        try:
            with open(key_file, "r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped:
                        keys.append(stripped)
        except Exception as e:
            app_logger.error(f"API anahtarları okunamadı ({endpoint_id}): {e}")
    return keys


def save_api_keys(endpoint_id: str, keys: list[str]):
    """API anahtarlarını dosyaya yazar (satır bazlı)."""
    os.makedirs(MCP_KEYS_FOLDER, exist_ok=True)
    key_file = os.path.join(MCP_KEYS_FOLDER, f"{endpoint_id}.txt")
    with open(key_file, "w", encoding="utf-8") as f:
        f.write("\n".join(keys))


# ─────────────────────── Key Pool Yöneticisi ───────────────────────


class KeyPool:
    """Bir endpoint için API anahtar havuzu yönetir."""

    def __init__(self, endpoint_id: str, use_rotation: bool = True):
        self.endpoint_id = endpoint_id
        self.use_rotation = use_rotation
        self.keys = load_api_keys(endpoint_id)
        self._index = 0

    def get_key(self) -> str | None:
        """Havuzdan bir anahtar döndürür."""
        if not self.keys:
            return None
        if self.use_rotation:
            key = self.keys[self._index % len(self.keys)]
            self._index += 1
            return key
        return self.keys[0]

    def has_keys(self) -> bool:
        return len(self.keys) > 0


# ─────────────────────── LLM Provider ───────────────────────


class LLMProvider:
    """
    Farklı LLM servislerine bağlanabilme soyutlaması.

    Kullanım:
        provider = LLMProvider(endpoint_id="default_gemini")
        # veya
        provider = LLMProvider(endpoint={"id":..., "type":..., ...}, api_key="xxx")

        result = provider.generate(prompt_text)
        tokens = provider.count_tokens(text)
    """

    def __init__(self, endpoint_id: str = None, endpoint: dict = None, api_key: str = None):
        """
        Args:
            endpoint_id: MCP_Endpoints.json'daki endpoint ID.  endpoint parametresi verilmemişse kullanılır.
            endpoint:    Doğrudan endpoint dict.  Verilirse endpoint_id yok sayılır.
            api_key:     Eski uyumluluk: doğrudan tek bir API anahtarı.  Verilirse key pool atlanır.
        """
        if endpoint:
            self.endpoint = endpoint
        elif endpoint_id:
            self.endpoint = get_endpoint_by_id(endpoint_id)
        else:
            self.endpoint = get_active_endpoint()

        if not self.endpoint:
            raise ValueError("Geçerli bir LLM endpoint bulunamadı.")

        self.ep_type = self.endpoint.get("type", "gemini")
        self.model_id = self.endpoint.get("model_id", "gemini-2.5-flash")
        self.base_url = self.endpoint.get("base_url")
        self.headers = self.endpoint.get("headers", {})
        self.ep_id = self.endpoint.get("id", "unknown")
        self.ep_name = self.endpoint.get("name", self.ep_id)

        # API anahtarı
        if api_key:
            self._key_pool = None
            self._single_key = api_key
        else:
            self._key_pool = KeyPool(
                self.ep_id,
                self.endpoint.get("use_key_rotation", True)
            )
            self._single_key = None

        # Kaç anahtar denendi (pool rotasyon takibi için)
        # 1: İlk anahtar başlangıçta sayılır (_ensure_* çağrısında alınır)
        self._tried_key_count = 1

        # Thread-safe istemci yeniden başlatma kilidi
        import threading
        self._client_lock = threading.Lock()

        # Dahili istemciler (lazy init)
        self._gemini_model = None
        self._openai_client = None

    # ──────── Anahtar alma ────────

    def _get_api_key(self) -> str:
        if self._single_key:
            return self._single_key
        if self._key_pool and self._key_pool.has_keys():
            return self._key_pool.get_key()
        raise ValueError(f"'{self.ep_name}' için API anahtarı bulunamadı.")

    # ──────── Gemini ────────

    def _ensure_gemini(self):
        if self._gemini_model is None:
            with self._client_lock:
                if self._gemini_model is None:  # double-checked locking
                    from google import genai
                    self._gemini_client = genai.Client(api_key=self._get_api_key())
                    self._gemini_model = "initialized"  # Bayrak olarak kullanıyoruz

    def _gemini_generate(self, prompt: str) -> str:
        self._ensure_gemini()
        response = self._gemini_client.models.generate_content(
            model=self.model_id,
            contents=prompt
        )
        if hasattr(response, 'prompt_feedback') and response.prompt_feedback and response.prompt_feedback.block_reason:
            raise Exception(f"İçerik engellendi: {response.prompt_feedback.block_reason.name}")
        if not response.text:
            raise Exception("API'den boş veya geçersiz metin alındı.")
        return response.text

    def _gemini_count_tokens(self, text: str) -> int:
        self._ensure_gemini()
        response = self._gemini_client.models.count_tokens(
            model=self.model_id,
            contents=text
        )
        return response.total_tokens

    # ──────── OpenAI-Uyumlu ────────

    def _ensure_openai(self):
        if self._openai_client is None:
            with self._client_lock:
                if self._openai_client is None:  # double-checked locking
                    try:
                        from openai import OpenAI
                    except ImportError:
                        raise ImportError("openai paketi yüklü değil.  Lütfen `pip install openai` ile yükleyin.")
                    self._openai_client = OpenAI(
                        api_key=self._get_api_key(),
                        base_url=self.base_url,
                        default_headers=self.headers if self.headers else None
                    )

    def rotate_key(self) -> bool:
        """
        Pool içinde bir sonraki API anahtarına geçer (429 sonrası çağrılır).

        Dönüş değeri:
          True  → Yeni anahtar mevcut, istemci sıfırlandı. Devam et.
          False → Havuzdaki tüm anahtarlar tükendi. Endpoint değiştir.

        NOT: Bu metot dışarıdan data_lock ile korunarak çağrılmalıdır.
        """
        # Tek anahtar modu: rotasyon yok
        if self._single_key is not None:
            return False
        # Havuz yok veya boş
        if self._key_pool is None or len(self._key_pool.keys) == 0:
            return False
        # Tüm anahtarlar denendi mi?
        if self._tried_key_count >= len(self._key_pool.keys):
            app_logger.info(
                f"Pool tükendi: '{self.ep_name}' — "
                f"{self._tried_key_count}/{len(self._key_pool.keys)} anahtar denendi."
            )
            return False

        self._tried_key_count += 1
        # Gemini / OpenAI istemcisini sıfırla; bir sonraki _ensure_* çağrısında
        # _key_pool.get_key() sıradaki anahtarı verecek.
        with self._client_lock:
            self._gemini_model = None
            self._gemini_client = None
            self._openai_client = None

        app_logger.info(
            f"Pool anahtarı rotasyonu: '{self.ep_name}' "
            f"({self._tried_key_count}/{len(self._key_pool.keys)}. anahtar kullanılacak)"
        )
        return True

    def _openai_generate(self, prompt: str) -> str:
        self._ensure_openai()
        response = self._openai_client.chat.completions.create(
            model=self.model_id,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        if not response.choices:
            raise Exception("API'den boş yanıt alındı.")
        return response.choices[0].message.content

    def _openai_count_tokens(self, text: str) -> int:
        """OpenAI-uyumlu servisler için yaklaşık token sayısı (karakter/4 tahmini)."""
        # tiktoken mevcut ise kullan, yoksa basit tahmini yap
        try:
            import tiktoken
            enc = tiktoken.encoding_for_model(self.model_id)
            return len(enc.encode(text))
        except Exception:
            # Basit tahmin: ~4 karakter ≈ 1 token
            return max(1, len(text) // 4)

    # ──────── Genel API ────────

    def generate(self, prompt: str) -> str:
        """Prompt göndererek LLM'den yanıt alır."""
        if self.ep_type == "gemini":
            return self._gemini_generate(prompt)
        else:
            return self._openai_generate(prompt)

    def count_tokens(self, text: str) -> int:
        """Metnin token sayısını hesaplar."""
        if self.ep_type == "gemini":
            return self._gemini_count_tokens(text)
        else:
            return self._openai_count_tokens(text)

    def test_connection(self) -> tuple[bool, str]:
        """Hızlı bağlantı testi yapar.  (success, message) döndürür."""
        try:
            result = self.generate("Merhaba, bu bir bağlantı testidir. Sadece 'OK' yaz.")
            if result:
                return True, f"Bağlantı başarılı. Yanıt: {result[:100]}"
            return False, "Boş yanıt alındı."
        except Exception as e:
            return False, f"Bağlantı hatası: {str(e)}"

    def get_info(self) -> dict:
        """Endpoint bilgilerini döndürür (UI için)."""
        return {
            "id": self.ep_id,
            "name": self.ep_name,
            "type": self.ep_type,
            "model_id": self.model_id,
            "base_url": self.base_url or "(varsayılan)",
        }


# ─────────────────── Geriye Uyumluluk ───────────────────

def create_provider_from_config(project_path: str, fallback_api_key: str = None) -> LLMProvider:
    """
    Proje config'inden veya global ayarlardan bir LLMProvider oluşturur.

    Proje config'inde `mcp_endpoint_id` varsa onu kullanır,
    yoksa global aktif endpoint'i kullanır,
    o da yoksa fallback_api_key ile Gemini provider oluşturur.
    """
    import configparser

    config_path = os.path.join(project_path, "config", "config.ini")
    config = configparser.ConfigParser()

    project_endpoint_id = None
    api_key = fallback_api_key

    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config.read_file(f)
            project_endpoint_id = config.get("MCP", "endpoint_id", fallback=None)
            if not api_key:
                api_key = config.get("API", "gemini_api_key", fallback=None)
        except Exception:
            pass

    # 1. Proje bazlı endpoint
    if project_endpoint_id:
        try:
            return LLMProvider(endpoint_id=project_endpoint_id)
        except Exception as e:
            app_logger.warning(f"Proje endpoint'i yüklenemedi ({project_endpoint_id}): {e}")

    # 2. Global aktif endpoint
    try:
        active = get_active_endpoint()
        if active:
            # Aktif endpoint için anahtar havuzunda anahtar var mı kontrol et
            pool = KeyPool(active["id"])
            if pool.has_keys():
                return LLMProvider(endpoint=active)
    except Exception as e:
        app_logger.warning(f"Global endpoint yüklenemedi: {e}")

    # 3. Geriye uyumluluk: doğrudan API key ile Gemini
    if api_key:
        return LLMProvider(
            endpoint={
                "id": "legacy_gemini",
                "name": "Eski Gemini",
                "type": "gemini",
                "model_id": "gemini-2.5-flash",
                "base_url": None,
                "use_key_rotation": False,
                "headers": {}
            },
            api_key=api_key
        )

    raise ValueError("Hiçbir LLM endpoint'i veya API anahtarı bulunamadı.")
