import json
import pickle
from typing import Optional, Any
from backend.app.config import settings

class RedisCache:
    """
    Redis caching layer for response caching, session management, and RAG result caching.
    Falls back to in-memory cache if Redis is not available.
    """

    def __init__(self):
        self.redis_client = None
        self.memory_cache = {}  # Fallback in-memory cache
        self.use_redis = False

        if not settings.REDIS_ENABLED:
            self.use_redis = False
            return

        try:
            import redis
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST if hasattr(settings, 'REDIS_HOST') else 'localhost',
                port=settings.REDIS_PORT if hasattr(settings, 'REDIS_PORT') else 6379,
                db=0,
                decode_responses=False,
                socket_connect_timeout=0.2,
                socket_timeout=0.2
            )
            # Test connection
            self.redis_client.ping()
            self.use_redis = True
            print("[RedisCache] Connected to Redis successfully")
        except Exception as e:
            print(f"[RedisCache] Redis not available, using in-memory cache: {e}")
            self.use_redis = False

    def _serialize(self, value: Any) -> bytes:
        """Serialize value for storage"""
        try:
            return pickle.dumps(value)
        except (pickle.PickleError, AttributeError):
            return json.dumps(value).encode('utf-8')

    def _deserialize(self, value: bytes) -> Any:
        """Deserialize value from storage"""
        try:
            return pickle.loads(value)
        except (pickle.PickleError, AttributeError):
            try:
                return json.loads(value.decode('utf-8'))
            except json.JSONDecodeError:
                return value.decode('utf-8')

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if self.use_redis and self.redis_client:
            try:
                value = self.redis_client.get(key)
                if value:
                    return self._deserialize(value)
            except Exception as e:
                print(f"[RedisCache] Error getting from Redis: {e}")

        # Fallback to memory cache
        return self.memory_cache.get(key)

    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in cache with TTL (default 1 hour)"""
        serialized = self._serialize(value)

        if self.use_redis and self.redis_client:
            try:
                self.redis_client.setex(key, ttl, serialized)
                return True
            except Exception as e:
                print(f"[RedisCache] Error setting in Redis: {e}")

        # Fallback to memory cache
        self.memory_cache[key] = value
        return True

    def delete(self, key: str) -> bool:
        """Delete value from cache"""
        if self.use_redis and self.redis_client:
            try:
                self.redis_client.delete(key)
            except Exception as e:
                print(f"[RedisCache] Error deleting from Redis: {e}")

        # Fallback to memory cache
        if key in self.memory_cache:
            del self.memory_cache[key]
        return True

    def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if self.use_redis and self.redis_client:
            try:
                return bool(self.redis_client.exists(key))
            except Exception as e:
                print(f"[RedisCache] Error checking existence in Redis: {e}")

        # Fallback to memory cache
        return key in self.memory_cache

    def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching a pattern"""
        count = 0
        if self.use_redis and self.redis_client:
            try:
                keys = self.redis_client.keys(pattern)
                if keys:
                    count = self.redis_client.delete(*keys)
            except Exception as e:
                print(f"[RedisCache] Error clearing pattern in Redis: {e}")

        # Fallback to memory cache (simple pattern matching)
        keys_to_delete = [k for k in self.memory_cache.keys() if pattern.replace('*', '') in k]
        for key in keys_to_delete:
            del self.memory_cache[key]
            count += 1

        return count

    def get_stats(self) -> dict:
        """Get cache statistics"""
        stats = {
            "backend": "redis" if self.use_redis else "memory",
            "keys": 0
        }

        if self.use_redis and self.redis_client:
            try:
                info = self.redis_client.info()
                stats["keys"] = info.get("db0", {}).get("keys", 0)
                stats["memory_used"] = info.get("used_memory_human", "N/A")
                stats["hits"] = info.get("keyspace_hits", 0)
                stats["misses"] = info.get("keyspace_misses", 0)
            except Exception as e:
                print(f"[RedisCache] Error getting Redis stats: {e}")
        else:
            stats["keys"] = len(self.memory_cache)

        return stats

# Global cache instance
cache_instance = None

def get_cache() -> RedisCache:
    """Get or create global cache instance"""
    global cache_instance
    if cache_instance is None:
        cache_instance = RedisCache()
    return cache_instance