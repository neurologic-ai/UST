from loguru import logger
from manager import settings
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
                settings.MONGO_URI,
                maxPoolSize=700,
                minPoolSize=10,
                driver=DRIVER_INFO
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
    try:
        logger.info("Checking and creating database indexes...")
        
        # Define collections and their index specifications
        collections_with_indexes = [
            # Association collections with 4-field compound index
            (breakfast_association_collection_name, 
             [("tenant_id", 1), ("location_id", 1), ("store_id", 1), ("product", 1)],
             "tenant_id_1_location_id_1_store_id_1_product_1"),
            (lunch_association_collection_name,
             [("tenant_id", 1), ("location_id", 1), ("store_id", 1), ("product", 1)],
             "tenant_id_1_location_id_1_store_id_1_product_1"),
            (dinner_association_collection_name,
             [("tenant_id", 1), ("location_id", 1), ("store_id", 1), ("product", 1)],
             "tenant_id_1_location_id_1_store_id_1_product_1"),
            (other_association_collection_name,
             [("tenant_id", 1), ("location_id", 1), ("store_id", 1), ("product", 1)],
             "tenant_id_1_location_id_1_store_id_1_product_1"),
            # Popular collections with 3-field compound index
            (breakfast_popular_collection_name,
             [("tenant_id", 1), ("location_id", 1), ("store_id", 1)],
             "tenant_id_1_location_id_1_store_id_1"),
            (lunch_popular_collection_name,
             [("tenant_id", 1), ("location_id", 1), ("store_id", 1)],
             "tenant_id_1_location_id_1_store_id_1"),
            (dinner_popular_collection_name,
             [("tenant_id", 1), ("location_id", 1), ("store_id", 1)],
             "tenant_id_1_location_id_1_store_id_1"),
            (other_popular_collection_name,
             [("tenant_id", 1), ("location_id", 1), ("store_id", 1)],
             "tenant_id_1_location_id_1_store_id_1"),
            # Lookup collection with 2-field compound index
            (lookup_collection,
             [("tenant_id", 1), ("location_id", 1)],
             "tenant_id_1_location_id_1"),
             (category_cache_collection,
             [("tenant_id", 1), ("location_id", 1)],
             "tenant_id_1_location_id_1")
        ]
        
        for collection, index_spec, index_name in collections_with_indexes:
            try:
                # Check if index already exists
                existing_indexes = await collection.list_indexes().to_list(None)
                index_exists = any(idx.get('name') == index_name for idx in existing_indexes)
                
                if index_exists:
                    logger.info(f"Index {index_name} already exists on {collection.name}")
                    continue
                
                # If index doesn't exist, check for duplicates before creating unique index
                logger.info(f"Checking for duplicates in {collection.name}...")
                
                # Build the key fields from index_spec
                key_fields = [field[0] for field in index_spec]
                
                # Find duplicates using aggregation
                pipeline = [
                    {
                        "$group": {
                            "_id": {field: f"${field}" for field in key_fields},
                            "count": {"$sum": 1},
                            "docs": {"$push": "$_id"}
                        }
                    },
                    {"$match": {"count": {"$gt": 1}}}
                ]
                
                duplicates = await collection.aggregate(pipeline).to_list(None)
                
                if duplicates:
                    logger.warning(f"Found {len(duplicates)} duplicate groups in {collection.name}")
                    
                    # Remove duplicates, keeping only the first document
                    for dup in duplicates:
                        doc_ids = dup['docs']
                        # Keep the first document, delete the rest
                        if len(doc_ids) > 1:
                            ids_to_delete = doc_ids[1:]  # Skip the first one
                            result = await collection.delete_many({"_id": {"$in": ids_to_delete}})
                            logger.info(f"Deleted {result.deleted_count} duplicate documents from {collection.name}")
                
                # Now create the unique index
                await collection.create_index(index_spec, unique=True, name=index_name)
                logger.info(f"Created unique index {index_name} on {collection.name}")
                
            except Exception as e:
                logger.error(f"Error processing index for {collection.name}: {e}")
                # Continue with other collections even if one fails
                continue
        
        logger.info("Database index creation process completed")
        
    except Exception as e:
        logger.error(f"Error in create_index: {e}")
        # Don't raise the exception to prevent startup failure
        # Indexes can be created manually later if needed





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