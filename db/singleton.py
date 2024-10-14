
from loguru import logger
from configs.manager import settings
from motor import motor_asyncio, core
from odmantic import AIOEngine
from pymongo.driver_info import DriverInfo

DRIVER_INFO = DriverInfo(name="full-stack-fastapi-mongodb", version="0.0.1")

#how to close the connection

class _MongoClientSingleton:
    mongo_client: motor_asyncio.AsyncIOMotorClient | None
    engine: AIOEngine

    def __new__(cls):
        if not hasattr(cls, "instance"):
            cls.instance = super(_MongoClientSingleton, cls).__new__(cls)
            cls.instance.mongo_client = motor_asyncio.AsyncIOMotorClient(
                settings.MONGO_URI, driver=DRIVER_INFO
            )
            cls.instance.engine = AIOEngine(client=cls.instance.mongo_client, database=settings.DB_NAME)
        return cls.instance 


def MongoDatabase() -> core.AgnosticDatabase:
    return _MongoClientSingleton().mongo_client[settings.DB_NAME]


def get_engine() -> AIOEngine:
    return _MongoClientSingleton().engine


async def ping():
    await MongoDatabase().command("ping")

async def close_connection():
    await _MongoClientSingleton().mongo_client.close()


popular_collection_name = MongoDatabase()['popular_collection']
time_collection_name = MongoDatabase()['time_collection']
weather_collection_name = MongoDatabase()['weather_collection']
calendar_collection_name = MongoDatabase()['calendar_collection']
association_collection_name = MongoDatabase()['association_collection']

__all__ = ["MongoDatabase", "get_engine","ping", "close_connection","popular_collection_name", "time_collection_name", "weather_collection_name", "calendar_collection_name", "association_collection_name"]