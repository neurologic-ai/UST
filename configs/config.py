import os
from dotenv import load_dotenv
load_dotenv()

env = os.getenv("ENV")

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "recommendation_db"
CATEGORY_DATA_LOCATION = './db/Categories.csv'