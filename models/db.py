from odmantic import Model
from typing import Dict

class User(Model):
    username: str
    password: str
    permissions: list[str] = []

    model_config = {
        "collection": "user_collection"
    }


class BreakfastPopular(Model):
    location_id: int
    store_id: int
    popular_data: Dict[str, int]

    model_config = {
        "collection": "breakfast_popular_collection"
    }

class LunchPopular(Model):
    location_id: int
    store_id: int
    popular_data: Dict[str, int]

    model_config = {
        "collection": "lunch_popular_collection"
    }

class DinnerPopular(Model):
    location_id: int
    store_id: int
    popular_data: Dict[str, int]

    model_config = {
        "collection": "dinner_popular_collection"
    }

class OtherPopular(Model):
    location_id: int
    store_id: int
    popular_data: Dict[str, int]

    model_config = {
        "collection": "other_popular_collection"
    }
    
class BreakfastAssociation(Model):
    location_id: int
    store_id: int
    product: str
    associate_products: Dict[str, int]

    model_config = {
        "collection": "breakfast_association_collection"
    }

class LunchAssociation(Model):
    location_id: int
    store_id: int
    product: str
    associate_products: Dict[str, int]

    model_config = {
        "collection": "lunch_association_collection"
    }

class DinnerAssociation(Model):
    location_id: int
    store_id: int
    product: str
    associate_products: Dict[str, int]

    model_config = {
        "collection": "dinner_association_collection"
    }

class OtherAssociation(Model):
    location_id: int
    store_id: int
    product: str
    associate_products: Dict[str, int]

    model_config = {
        "collection": "other_association_collection"
    }