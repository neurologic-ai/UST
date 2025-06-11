# redis_client.py
import redis
from configs.manager import settings


def get_redis_client() -> redis.Redis:
    return redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)
