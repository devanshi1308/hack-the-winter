"""Database layer for RaAI."""

from .mongo import MongoDB, get_mongo

__all__ = ["MongoDB", "get_mongo"]
