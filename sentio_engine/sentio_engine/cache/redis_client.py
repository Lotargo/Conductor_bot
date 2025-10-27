import os
import redis
from fakeredis import FakeStrictRedis

_redis_pool = None
_fake_redis_instance = None

def get_redis_client():
    """
    Returns a singleton Redis client instance.
    In testing mode (determined by the 'TESTING' env var), it uses fakeredis.
    """
    testing = os.getenv("TESTING", "false").lower() == "true"

    if testing:
        global _fake_redis_instance
        if _fake_redis_instance is None:
            _fake_redis_instance = FakeStrictRedis()
        return _fake_redis_instance

    global _redis_pool
    if _redis_pool is None:
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        _redis_pool = redis.ConnectionPool(host=redis_host, port=redis_port, db=0)

    return redis.Redis(connection_pool=_redis_pool)
