"""
MagicLamp Repository Layer
Provides domain-specific database access patterns between DatabaseClient and API routes.
"""

from .user import UserRepository
from .fact import FactRepository

__all__ = ["UserRepository", "FactRepository"]
