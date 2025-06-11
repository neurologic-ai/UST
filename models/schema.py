from datetime import datetime
import uuid
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from bson import ObjectId
from typing import Any


class RecommendationRequestBody(BaseModel):
    cartItems: list[str]
    topN: int
    currentHour: int
    currentDateTime: datetime
    tenantId: str
    locationId: str
    storeId: str
    latitude: float
    longitude: float
    

class UserBase(BaseModel):
    username: str
    password: str

class LoginData(UserBase):
    pass

class UserCreate(UserBase):
    permissions: list[str] = []

class PyUser(UserBase):
    id: Any
    permissions: list[str] = []

class Token(BaseModel):
    access_token: str
    token_type: str

def to_serializable(doc):
    """Convert MongoDB ObjectId to string."""
    if isinstance(doc, ObjectId):
        return str(doc)
    return doc



# class StoreModel(BaseModel):
#     store_id: str 
#     name: str


# class LocationModel(BaseModel):
#     location_id: str 
#     name: str
#     stores: List[StoreModel] = []


# class TenantCreate(BaseModel):
#     tenant_name: str
#     locations: List[LocationModel] = []

# class TenantUpdate(BaseModel):
#     tenant_id: str
#     tenant_name: str
#     locations: List[LocationModel] = []

class StoreModel(BaseModel):
    store_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str

    class Config:
        json_schema_extra = {
            "example": {
                "store_id": "store_1",
                "name": "Connaught Place Store"
            }
        }

class LocationModel(BaseModel):
    location_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    stores: List[StoreModel] = []

    class Config:
        json_schema_extra = {
            "example": {
                "location_id": "location_1",
                "name": "Delhi HQ",
                "stores": [
                    {
                        "store_id": "store_1",
                        "name": "Connaught Place Store"
                    },
                    {
                        "store_id": "store_2",
                        "name": "Saket Store"
                    }
                ]
            }
        }

class TenantCreate(BaseModel):
    tenant_name: str
    locations: List[LocationModel] = []

    class Config:
        json_schema_extra = {
            "example": {
                "tenant_name": "Dominos",
                "locations": [
                    {
                        "location_id": "location_1",
                        "name": "Delhi HQ",
                        "stores": [
                            {"store_id": "store_1", "name": "Connaught Place Store"},
                            {"store_id": "store_2", "name": "Saket Store"}
                        ]
                    },
                    {
                        "location_id": "location_2",
                        "name": "Mumbai Branch",
                        "stores": [
                            {"store_id": "store_3", "name": "Bandra Store"}
                        ]
                    }
                ]
            }
        }

class TenantUpdate(BaseModel):
    tenant_id: str
    tenant_name: Optional[str] = None
    locations: Optional[List[LocationModel]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "tenant_id": "682b5a70a9f70088c6d85448",
                "tenant_name": "Dominos Updated",
                "locations": [
                    {
                        "location_id": "location_1",
                        "name": "Delhi HQ",
                        "stores": [
                            {
                                "store_id": "store_1",
                                "name": "Connaught Place Store"
                            },
                            {
                                "store_id": "store_2",
                                "name": "Saket Store"
                            }
                        ]
                    },
                    {
                        "location_id": "location_2",
                        "name": "Mumbai Branch",
                        "stores": [
                            {
                                "store_id": "store_3",
                                "name": "Bandra Store"
                            }
                        ]
                    }
                ]
            }
        }