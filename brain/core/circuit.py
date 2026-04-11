"""
MagicLamp — Circuit Breaker
Prevents cascade failures when external services (Ollama, Supabase) go down.
States: CLOSED (normal) → OPEN (failing) → HALF_OPEN (testing recovery)
"""

import asyncio
import time
from enum import Enum
from typing import Callable, Any
from core.logger import get_logger

log = get_logger("circuit_breaker")


class CircuitState(Enum):
    CLOSED = "closed"  # Normal — requests pass through
    OPEN = "open"  # Failing — requests blocked immediately
    HALF_OPEN = "half_open"  # Testing — one request allowed through


class CircuitBreaker:
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        success_threshold: int = 2,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float = 0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._success_count = 0
                log.info(f"[{self.name}] Circuit HALF_OPEN — testing recovery")
        return self._state

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        async with self._lock:
            state = self.state

        if state == CircuitState.OPEN:
            raise CircuitOpenError(f"[{self.name}] Circuit is OPEN — service unavailable")

        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as e:
            await self._on_failure(e)
            raise

    async def _on_success(self):
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    log.info(f"[{self.name}] Circuit CLOSED — service recovered")
            else:
                self._failure_count = 0

    async def _on_failure(self, exc: Exception):
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            if self._failure_count >= self.failure_threshold:
                if self._state != CircuitState.OPEN:
                    self._state = CircuitState.OPEN
                    log.warning(f"[{self.name}] Circuit OPEN — {self._failure_count} failures. Error: {exc}")

    def get_status(self) -> dict:
        return {
            "name": self.name,
            "state": self.state.value,
            "failures": self._failure_count,
        }


class CircuitOpenError(Exception):
    pass


# Global circuit breakers
ollama_circuit = CircuitBreaker("ollama", failure_threshold=3, recovery_timeout=20)
supabase_circuit = CircuitBreaker("supabase", failure_threshold=5, recovery_timeout=30)
telegram_circuit = CircuitBreaker("telegram", failure_threshold=5, recovery_timeout=60)
n8n_circuit = CircuitBreaker("n8n", failure_threshold=3, recovery_timeout=30)
