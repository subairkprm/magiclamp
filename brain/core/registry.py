"""
MagicLamp — Module Registry
Every module registers itself here. The registry knows all modules,
their versions, health status, and routes.
"""
import asyncio
from typing import Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from core.logger import get_logger

log = get_logger("registry")

@dataclass
class HealthStatus:
    healthy:  bool = True
    message:  str  = "OK"
    details:  dict = field(default_factory=dict)

class BaseModule(ABC):
    """All modules must inherit this."""
    name:         str = "base"
    version:      str = "1.0.0"
    description:  str = ""
    dependencies: list[str] = []

    @abstractmethod
    async def initialize(self) -> bool:
        """Called once at startup."""
        ...

    @abstractmethod
    async def health_check(self) -> HealthStatus:
        """Called periodically by health monitor."""
        ...

    async def shutdown(self) -> None:
        """Called on graceful shutdown."""
        pass

class ModuleRegistry:
    def __init__(self):
        self._modules: dict[str, BaseModule] = {}
        self._health:  dict[str, HealthStatus] = {}
        self._initialized = False

    def register(self, module: BaseModule):
        self._modules[module.name] = module
        log.info(f"[Registry] Registered: {module.name} v{module.version}")

    async def initialize_all(self):
        for name, module in self._modules.items():
            try:
                ok = await module.initialize()
                if ok:
                    log.info(f"[Registry] Initialized: {name}")
                else:
                    log.warning(f"[Registry] Init returned False: {name}")
            except Exception as e:
                log.warning(f"[Registry] Init failed: {name} — {e}")
        self._initialized = True

    async def health_check_all(self) -> dict[str, HealthStatus]:
        results = {}
        for name, module in self._modules.items():
            try:
                status = await asyncio.wait_for(module.health_check(), timeout=5.0)
                results[name] = status
                self._health[name] = status
            except asyncio.TimeoutError:
                results[name] = HealthStatus(False, "Health check timed out")
            except Exception as e:
                results[name] = HealthStatus(False, str(e))
        return results

    async def shutdown_all(self):
        for name, module in reversed(list(self._modules.items())):
            try:
                await module.shutdown()
                log.info(f"[Registry] Shutdown: {name}")
            except Exception as e:
                log.warning(f"[Registry] Shutdown error: {name} — {e}")

    def get(self, name: str) -> Optional[BaseModule]:
        return self._modules.get(name)

    def list_modules(self) -> list[dict]:
        return [
            {
                "name": m.name,
                "version": m.version,
                "description": m.description,
                "health": self._health.get(m.name, HealthStatus()).healthy,
            }
            for m in self._modules.values()
        ]

    def get_all_routes(self) -> list:
        routes = []
        for module in self._modules.values():
            if hasattr(module, "get_routes"):
                routes.extend(module.get_routes())
        return routes

registry = ModuleRegistry()
