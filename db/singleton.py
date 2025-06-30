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
                settings.MONGO_URI, driver = DRIVER_INFO
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
    _MongoClientSingleton().mongo_client.close()


breakfast_association_collection_name = MongoDatabase()['breakfast_association_collection']
lunch_association_collection_name = MongoDatabase()['lunch_association_collection']
dinner_association_collection_name = MongoDatabase()['dinner_association_collection']
other_association_collection_name = MongoDatabase()['other_association_collection']

breakfast_popular_collection_name = MongoDatabase()['breakfast_popular_collection']
lunch_popular_collection_name = MongoDatabase()['lunch_popular_collection']
dinner_popular_collection_name = MongoDatabase()['dinner_popular_collection']
other_popular_collection_name = MongoDatabase()['other_popular_collection']

lookup_collection = MongoDatabase()['lookup_dicts']
category_cache_collection = MongoDatabase()["category_cache"]

async def create_index():
    await breakfast_association_collection_name.create_index([("tenant_id", 1), ("location_id", 1), ("store_id", 1)])
    await lunch_association_collection_name.create_index([("tenant_id", 1), ("location_id", 1), ("store_id", 1)])
    await dinner_association_collection_name.create_index([("tenant_id", 1), ("location_id", 1), ("store_id", 1)])
    await other_association_collection_name.create_index([("tenant_id", 1), ("location_id", 1), ("store_id", 1)])
    await breakfast_popular_collection_name.create_index([("tenant_id", 1), ("location_id", 1), ("store_id", 1)])
    await lunch_popular_collection_name.create_index([("tenant_id", 1), ("location_id", 1), ("store_id", 1)])
    await dinner_popular_collection_name.create_index([("tenant_id", 1), ("location_id", 1), ("store_id", 1)])
    await other_popular_collection_name.create_index([("tenant_id", 1), ("location_id", 1), ("store_id", 1)])
    await lookup_collection.create_index([("tenant_id", 1), ("location_id", 1)])
    await category_cache_collection.create_index([("tenant_id", 1), ("location_id", 1)])



__all__ = ["MongoDatabase", 
           "get_engine",
           "ping", 
           "close_connection",
           "breakfast_association_collection_name",
           "lunch_association_collection_name",
           "dinner_association_collection_name",
           "other_association_collection_name",
           "breakfast_popular_collection_name",
           "lunch_popular_collection_name",
           "dinner_popular_collection_name",
           "other_popular_collection_name"]