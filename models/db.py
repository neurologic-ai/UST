
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
    popular_data: Dict[str, int]

    model_config = {
        "collection": "breakfast_popular_collection"
    }

class LunchPopular(Model):
    popular_data: Dict[str, int]

    model_config = {
        "collection": "lunch_popular_collection"
    }

class DinnerPopular(Model):
    popular_data: Dict[str, int]

    model_config = {
        "collection": "dinner_popular_collection"
    }

class OtherPopular(Model):
    popular_data: Dict[str, int]

    model_config = {
        "collection": "other_popular_collection"
    }
    
class BreakfastAssociation(Model):
    product: str
    associate_products: Dict[str, int]

    model_config = {
        "collection": "breakfast_popular_collection"
    }

class LunchAssociation(Model):
    product: str
    associate_products: Dict[str, int]

    model_config = {
        "collection": "lunch_popular_collection"
    }

class DinnerAssociation(Model):
    product: str
    associate_products: Dict[str, int]

    model_config = {
        "collection": "dinner_popular_collection"
    }

class OtherAssociation(Model):
    product: str
    associate_products: Dict[str, int]

    model_config = {
        "collection": "other_popular_collection"
    }