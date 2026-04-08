"""
MagicLamp — Structured JSON Logging
Every log is machine-readable. Never use print() in production.
"""

import logging
import json
import sys
from datetime import datetime
from core.config import settings


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "module": record.name,
            "msg": record.getMessage(),
            "env": settings.ENVIRONMENT,
            "app": settings.APP_NAME,
        }
        if record.exc_info:
            log["exc"] = self.formatException(record.exc_info)
        if hasattr(record, "extra"):
            log.update(record.extra)
        return json.dumps(log, ensure_ascii=False)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO if settings.ENVIRONMENT == "production" else logging.DEBUG)
        logger.propagate = False
    return logger


log = get_logger("magiclamp")
