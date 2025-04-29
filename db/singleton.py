
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
            cls.instance.engine = AIOEngine(client=cls.instance.mongo_client)
        return cls.instance 


# def MongoDatabase() -> core.AgnosticDatabase:
#     return _MongoClientSingleton().mongo_client[settings.DB_NAME]
def MongoDatabase(tenant: str) -> core.AgnosticDatabase:
    tenant = tenant.replace("/", "_").replace("\\", "_").replace(" ", "_").strip()
    return _MongoClientSingleton().mongo_client[f"{tenant}_db"]


def get_engine() -> AIOEngine:
    return _MongoClientSingleton().engine

def get_tenant_collections(tenant: str):
    db = MongoDatabase(tenant)
    return {
        "breakfast_popular": db["breakfast_popular"],
        "lunch_popular": db["lunch_popular"],
        "dinner_popular": db["dinner_popular"],
        "other_popular": db["other_popular"],
        "breakfast_association": db["breakfast_association"],
        "lunch_association": db["lunch_association"],
        "dinner_association": db["dinner_association"],
        "other_association": db["other_association"]
    }


async def ping():
    await MongoDatabase().command("ping")

async def close_connection():
    await _MongoClientSingleton().mongo_client.close()


# breakfast_association_collection_name = MongoDatabase()['breakfast_association_collection']
# lunch_association_collection_name = MongoDatabase()['lunch_association_collection']
# dinner_association_collection_name = MongoDatabase()['dinner_association_collection']
# other_association_collection_name = MongoDatabase()['other_association_collection']

# breakfast_popular_collection_name = MongoDatabase()['breakfast_popular_collection']
# lunch_popular_collection_name = MongoDatabase()['lunch_popular_collection']
# dinner_popular_collection_name = MongoDatabase()['dinner_popular_collection']
# other_popular_collection_name = MongoDatabase()['other_popular_collection']

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