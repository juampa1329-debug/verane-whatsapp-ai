# app/utils/circuit_breaker.py

from __future__ import annotations
import time
from dataclasses import dataclass

@dataclass
class CircuitBreakerConfig:
    fail_threshold: int = 3
    cooldown_sec: int = 90

class CircuitBreaker:
    """
    Breaker simple en memoria (por proceso).
    - Si falla N veces, se abre por cooldown_sec.
    - Mientras esté abierto, se recomienda usar fallback (DB).
    """
    def __init__(self, cfg: CircuitBreakerConfig | None = None):
        self.cfg = cfg or CircuitBreakerConfig()
        self._fails = 0
        self._open_until = 0

    def is_open(self) -> bool:
        return int(time.time()) < int(self._open_until or 0)

    def record_success(self) -> None:
        self._fails = 0
        self._open_until = 0

    def record_failure(self) -> None:
        self._fails += 1
        if self._fails >= int(self.cfg.fail_threshold):
            self._open_until = int(time.time()) + int(self.cfg.cooldown_sec)

    def info(self) -> dict:
        return {
            "fails": int(self._fails),
            "open_until": int(self._open_until or 0),
            "is_open": bool(self.is_open()),
            "fail_threshold": int(self.cfg.fail_threshold),
            "cooldown_sec": int(self.cfg.cooldown_sec),
        }