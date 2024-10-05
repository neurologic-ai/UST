from pymongo.mongo_client import MongoClient
from configs.config import MONGO_URI

uri = MONGO_URI
print(uri)
client = MongoClient(uri)

db = client.recommendation_db

popular_collection_name = db['popular_collection']
time_collection_name = db['time_collection']
weather_collection_name = db['weather_collection']
calendar_collection_name = db['calendar_collection']
association_collection_name = db['association_collection']