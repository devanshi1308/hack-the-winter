import time
import json
import pickle
from typing import Any, Optional
from threading import Lock


class TTLCache:
    """
    Thread-safe in-memory cache with TTL (time-to-live) expiration.
    
    Usage:
        cache = TTLCache(ttl_seconds=60)
        cache.set("key", {"data": "value"})
        result = cache.get("key")  # Returns {"data": "value"} if not expired
    """
    
    def __init__(self, ttl_seconds: int = 60):
        """
        Initialize TTL cache.
        
        Args:
            ttl_seconds: Time-to-live in seconds for cached items (default: 60)
        """
        self.ttl = ttl_seconds
        self.cache = {}
        self.lock = Lock()

    def set(self, key: str, value: Any) -> None:
        """
        Store a value in cache with current timestamp.
        
        Args:
            key: Cache key (string)
            value: Value to cache (any serializable type)
        """
        with self.lock:
            self.cache[key] = (value, time.time())

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a value from cache if not expired.
        
        Args:
            key: Cache key to retrieve
            
        Returns:
            Cached value if exists and not expired, None otherwise
        """
        with self.lock:
            item = self.cache.get(key)
            if not item:
                return None
            
            value, timestamp = item
            
            # Check if expired
            if time.time() - timestamp > self.ttl:
                del self.cache[key]
                return None
            
            return value

    def delete(self, key: str) -> bool:
        """
        Delete a specific key from cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if key existed and was deleted, False otherwise
        """
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all items from cache."""
        with self.lock:
            self.cache.clear()

    def cleanup_expired(self) -> int:
        """
        Remove all expired items from cache.
        
        Returns:
            Number of items removed
        """
        with self.lock:
            current_time = time.time()
            expired_keys = [
                key for key, (_, timestamp) in self.cache.items()
                if current_time - timestamp > self.ttl
            ]
            
            for key in expired_keys:
                del self.cache[key]
            
            return len(expired_keys)

    def size(self) -> int:
        """
        Get current cache size (number of items).
        
        Returns:
            Number of items in cache
        """
        with self.lock:
            return len(self.cache)


# Optional: Redis cache wrapper
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False


class RedisTTLCache:
    """
    Redis-backed cache with TTL expiration.
    
    Requires redis-py: pip install redis
    
    Usage:
        cache = RedisTTLCache(host='localhost', ttl_seconds=60)
        cache.set("key", {"data": "value"})
        result = cache.get("key")
    """
    
    def __init__(
        self, 
        host: str = 'localhost', 
        port: int = 6379, 
        db: int = 0, 
        ttl_seconds: int = 60,
        password: Optional[str] = None,
        decode_responses: bool = False
    ):
        """
        Initialize Redis cache.
        
        Args:
            host: Redis host (default: localhost)
            port: Redis port (default: 6379)
            db: Redis database number (default: 0)
            ttl_seconds: Time-to-live in seconds (default: 60)
            password: Redis password (optional)
            decode_responses: Decode responses to strings (default: False)
        
        Raises:
            ImportError: If redis-py is not installed
            redis.ConnectionError: If cannot connect to Redis
        """
        if not REDIS_AVAILABLE:
            raise ImportError(
                'redis-py not installed. Install with: pip install redis'
            )
        
        self.client = redis.StrictRedis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=decode_responses
        )
        self.ttl = ttl_seconds
        
        # Test connection
        try:
            self.client.ping()
        except redis.ConnectionError as e:
            raise redis.ConnectionError(
                f"Cannot connect to Redis at {host}:{port}: {e}"
            )

    def set(self, key: str, value: Any) -> bool:
        """
        Store a value in Redis with TTL.
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON-serialized)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Serialize value as JSON
            serialized = json.dumps(value)
            return self.client.setex(key, self.ttl, serialized)
        except (TypeError, json.JSONDecodeError):
            # Fallback to pickle for non-JSON-serializable objects
            try:
                serialized = pickle.dumps(value)
                return self.client.setex(key, self.ttl, serialized)
            except Exception:
                return False

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a value from Redis.
        
        Args:
            key: Cache key to retrieve
            
        Returns:
            Cached value if exists, None otherwise
        """
        value = self.client.get(key)
        if value is None:
            return None
        
        # Try JSON deserialization first
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            # Fallback to pickle
            try:
                return pickle.loads(value)
            except Exception:
                return None

    def delete(self, key: str) -> bool:
        """
        Delete a key from Redis.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if key existed and was deleted, False otherwise
        """
        return self.client.delete(key) > 0

    def clear(self) -> None:
        """Clear all keys in current database."""
        self.client.flushdb()

    def exists(self, key: str) -> bool:
        """
        Check if a key exists in Redis.
        
        Args:
            key: Cache key to check
            
        Returns:
            True if key exists, False otherwise
        """
        return self.client.exists(key) > 0

    def ttl_remaining(self, key: str) -> int:
        """
        Get remaining TTL for a key.
        
        Args:
            key: Cache key
            
        Returns:
            Remaining seconds, or -2 if key doesn't exist, -1 if no TTL
        """
        return self.client.ttl(key)


def get_cache(use_redis: bool = False, **kwargs) -> TTLCache:
    """
    Factory function to get appropriate cache implementation.
    
    Args:
        use_redis: Whether to use Redis (requires redis-py)
        **kwargs: Additional arguments passed to cache constructor
        
    Returns:
        Cache instance (TTLCache or RedisTTLCache)
        
    Example:
        # In-memory cache
        cache = get_cache(ttl_seconds=120)
        
        # Redis cache
        cache = get_cache(
            use_redis=True,
            host='localhost',
            port=6379,
            ttl_seconds=60
        )
    """
    if use_redis:
        if not REDIS_AVAILABLE:
            raise ImportError(
                'Redis requested but redis-py not installed. '
                'Install with: pip install redis'
            )
        return RedisTTLCache(**kwargs)
    else:
        return TTLCache(**kwargs)