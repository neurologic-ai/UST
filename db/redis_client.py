from loguru import logger
import redis.asyncio as redis  # ✅ Use the asyncio-compatible Redis
from configs.manager import settings


def get_redis_client() -> redis.Redis:
    logger.debug(settings.REDIS_HOST)
    logger.debug(settings.REDIS_PORT)
    return redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        ssl=True,
        db=0,
        socket_connect_timeout=3,  # 300ms to establish connection
        socket_timeout=5           # 500ms max wait for response
    )
