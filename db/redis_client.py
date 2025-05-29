# redis_client.py
import redis
from fastapi import Depends

def get_redis_client() -> redis.Redis:
    return redis.Redis(host="localhost", port=6379, db=0)
