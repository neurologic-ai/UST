from pymongo.mongo_client import MongoClient
from configs.manager import settings
from loguru import logger

def ping_mongodb(uri):
    try:
        logger.info("Connecting to MongoDB...")
        # Create a MongoClient object
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)  # Timeout after 5 seconds

        # Ping the server
        client.admin.command('ping')
        logger.info("MongoDB server is available.")
        return client  # Return the client for further use

    except Exception as e:
        logger.exception(f"Could not connect to MongoDB: {e}")
        return None


uri = settings.MONGO_URI
client = ping_mongodb(uri)

db = client.recommendation_db

popular_collection_name = db['popular_collection']
time_collection_name = db['time_collection']
weather_collection_name = db['weather_collection']
calendar_collection_name = db['calendar_collection']
association_collection_name = db['association_collection']