import os
import json
import time
import threading
from collections import deque


class RateLimiter:
    """Kayan 60 sn penceresinde RPM ve TPM sınırı uygular (thread-safe)."""

    def __init__(self):
        self._lock = threading.Lock()
        self._events = deque()  # (zaman, token)
        self.rpm = 0
        self.tpm = 0

    def configure(self, rpm: int, tpm: int):
        self.rpm, self.tpm = rpm, tpm

    def acquire(self, tokens: int, stop_check=None) -> bool:
        while True:
            wait = 0.0
            with self._lock:
                now = time.monotonic()
                while self._events and now - self._events[0][0] >= 60:
                    self._events.popleft()

                if self.rpm and len(self._events) >= self.rpm:
                    wait = max(wait, 60 - (now - self._events[0][0]))

                if self.tpm and self._events:
                    running = sum(t for _, t in self._events)
                    if running + tokens > self.tpm:
                        wait = max(wait, 60 - (now - self._events[-1][0]))
                        for ts, tk in self._events:
                            running -= tk
                            if running + tokens <= self.tpm:
                                wait = max(wait, 60 - (now - ts))
                                break

                if wait <= 0:
                    self._events.append((now, tokens))
                    return True

            if stop_check and stop_check():
                return False
            time.sleep(min(wait, 1.0) + 0.05)


_limiter = RateLimiter()


def get_limiter() -> RateLimiter:
    """app_settings.json'dan ml_rpm_limit / ml_tpm_limit okur (0 = sınırsız)."""
    rpm, tpm = 5, 0
    try:
        path = os.path.join(os.getcwd(), 'AppConfigs', 'app_settings.json')
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            rpm = int(data.get('ml_rpm_limit', rpm))
            tpm = int(data.get('ml_tpm_limit', tpm))
    except Exception:
        pass
    _limiter.configure(rpm, tpm)
    return _limiter