from odmantic import EmbeddedModel, Model
from typing import Dict, List

from pydantic import BaseModel

class User(Model):
    username: str
    password: str
    permissions: list[str] = []

    model_config = {
        "collection": "user_collection"
    }

class PopularProductData(BaseModel):
    upc: str
    # upc: int
    count: int

class AssociationProductData(BaseModel):
    upc: str
    # upc: int
    count: int

# --- Popular Models ---
class BreakfastPopular(Model):
    tenant_id: str
    location_id: str
    store_id: str
    popular_data: Dict[str, PopularProductData]  # name: {upc, count}

    model_config = {
        "collection": "breakfast_popular_collection"
    }

class LunchPopular(Model):
    tenant_id: str
    location_id: str
    store_id: str
    popular_data: Dict[str, PopularProductData]

    model_config = {
        "collection": "lunch_popular_collection"
    }

class DinnerPopular(Model):
    tenant_id: str
    location_id: str
    store_id: str
    popular_data: Dict[str, PopularProductData]

    model_config = {
        "collection": "dinner_popular_collection"
    }

class OtherPopular(Model):
    tenant_id: str
    location_id: str
    store_id: str
    popular_data: Dict[str, PopularProductData]

    model_config = {
        "collection": "other_popular_collection"
    }

# --- Association Models ---
class BreakfastAssociation(Model):
    tenant_id: str
    location_id: str
    store_id: str
    product: str  # this can still be name or upc, depending on preference
    associate_products: Dict[str, AssociationProductData]  # name: {upc, count}

    model_config = {
        "collection": "breakfast_association_collection"
    }

class LunchAssociation(Model):
    tenant_id: str
    location_id: str
    store_id: str
    product: str
    associate_products: Dict[str, AssociationProductData]

    model_config = {
        "collection": "lunch_association_collection"
    }

class DinnerAssociation(Model):
    tenant_id: str
    location_id: str
    store_id: str
    product: str
    associate_products: Dict[str, AssociationProductData]

    model_config = {
        "collection": "dinner_association_collection"
    }

class OtherAssociation(Model):
    tenant_id: str
    location_id: str
    store_id: str
    product: str
    associate_products: Dict[str, AssociationProductData]

    model_config = {
        "collection": "other_association_collection"
    }


# class BreakfastPopular(Model):
#     tenant_id: str
#     location_id: str
#     store_id: str
#     popular_data: Dict[str, int]

#     model_config = {
#         "collection": "breakfast_popular_collection"
#     }

# class LunchPopular(Model):
#     tenant_id: str
#     location_id: str
#     store_id: str
#     popular_data: Dict[str, int]

#     model_config = {
#         "collection": "lunch_popular_collection"
#     }

# class DinnerPopular(Model):
#     tenant_id: str
#     location_id: str
#     store_id: str
#     popular_data: Dict[str, int]

#     model_config = {
#         "collection": "dinner_popular_collection"
#     }

# class OtherPopular(Model):
#     tenant_id: str
#     location_id: str
#     store_id: str
#     popular_data: Dict[str, int]

#     model_config = {
#         "collection": "other_popular_collection"
#     }
    
# class BreakfastAssociation(Model):
#     tenant_id: str
#     location_id: str
#     store_id: str
#     product: str
#     associate_products: Dict[str, int]

#     model_config = {
#         "collection": "breakfast_association_collection"
#     }

# class LunchAssociation(Model):
#     tenant_id: str
#     location_id: str
#     store_id: str
#     product: str
#     associate_products: Dict[str, int]

#     model_config = {
#         "collection": "lunch_association_collection"
#     }

# class DinnerAssociation(Model):
#     tenant_id: str
#     location_id: str
#     store_id: str
#     product: str
#     associate_products: Dict[str, int]

#     model_config = {
#         "collection": "dinner_association_collection"
#     }

# class OtherAssociation(Model):
#     ltenant_id: str
#     location_id: str
#     store_id: str
#     product: str
#     associate_products: Dict[str, int]

#     model_config = {
#         "collection": "other_association_collection"
#     }


class Store(EmbeddedModel):
    store_id: str
    name: str


class Location(EmbeddedModel):
    location_id: str
    name: str
    stores: List[Store] = []


class Tenant(Model):
    tenant_name: str
    api_key: str
    locations: List[Location] = []

    model_config = {
        "collection": "tenant_collection"
    }

class CategoryData(EmbeddedModel):
    name: str
    category: str
    subcategory: str
    timing: str

class CategoryCache(Model):
    tenant_id: str
    location_id: str
    data: Dict[str, CategoryData]  # product_name -> data

    model_config = {
        "collection": "category_cache"
    }