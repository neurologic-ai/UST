# redis_client.py
from loguru import logger
import redis
from configs.manager import settings


def get_redis_client() -> redis.Redis:
    logger.debug(settings.REDIS_HOST)
    logger.debug(settings.REDIS_PORT)
    return redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        ssl=True,
        db=0,
        socket_connect_timeout=0.3,  # 300ms to establish connection
        socket_timeout=0.5           # 500ms max wait for response
    )
