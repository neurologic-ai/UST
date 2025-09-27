from datetime import datetime
from odmantic import EmbeddedModel, Model, Field
from typing import Dict, List, Optional

from pydantic import BaseModel

from enum import Enum

class UserRole(str, Enum):
    ADMIN_UST = "ADMIN_UST"
    TENANT_ADMIN = "TENANT_ADMIN"
    UST_SUPPORT = "UST_SUPPORT"
    TENANT_OP = "TENANT_OP"

class UserStatus(str, Enum):
    ACTIVE = "Active"
    INACTIVE = "Inactive"


class User(Model):  # or Document if you're using Beanie
    username: str
    password: str
    permissions: List[str] = []

    role: UserRole
    name: str
    status: UserStatus = UserStatus.ACTIVE
    tenant_id: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None

    model_config = {
        "collection": "user_collection"
    }

class PopularProductData(BaseModel):
    upc: str
    count: int

class AssociationProductData(BaseModel):
    upc: str
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


class Store(EmbeddedModel):
    store_id: str
    name: str
    status: UserStatus = UserStatus.ACTIVE
    state: Optional[str] = None
    country: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None


class Location(EmbeddedModel):
    location_id: str
    name: str
    status: UserStatus = UserStatus.ACTIVE
    stores: List[Store] = []


class Tenant(Model):
    tenant_name: str
    normalized_name: str
    api_key: str
    locations: List[Location] = []
    created_at: datetime
    created_by: str
    updated_at: Optional[datetime]
    updated_by: Optional[str]
    status: UserStatus = UserStatus.ACTIVE

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