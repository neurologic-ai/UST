
from odmantic import Model
from typing import Dict, List

class User(Model):
    username: str
    password: str
    permissions: list[str] = []

    model_config = {
        "collection": "user_collection"
    }

    

class Association_collection(Model):
    product: str
    associate_products: Dict[str, int]

    model_config = {
        "collection": "association_collection"
    }

class Popular_collection(Model):
    popular_data: Dict[str, int]

    model_config = {
        "collection": "popular_collection"
    }

class Time_collection(Model):
    hour: int
    dayofweek: int
    recommended_products: List[str]

    model_config = {
        "collection": "time_collection"
    }

class Weather_collection(Model):
    category: str
    products: List[str]

    model_config = {
        "collection": "weather_collection"
    }

class Calendar_collection(Model):
    holiday: str
    products: List[str]

    model_config = {
        "collection": "calendar_collection"
    }

