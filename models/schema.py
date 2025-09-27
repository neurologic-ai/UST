from datetime import datetime
import uuid
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from bson import ObjectId
from typing import Any

from models.db import UserRole, UserStatus


class RecommendationRequestBody(BaseModel):
    cartItems: list[str]
    topN: int
    currentHour: int
    locationId: str
    storeId: str

    

class UserBase(BaseModel):
    username: str
    password: str

class LoginData(UserBase):
    pass

class UserCreate(UserBase):
    username: str
    password: str
    role: UserRole
    name: str
    tenantId: Optional[str] = None

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
    tenantName: str
    status: UserStatus
    apiKey: Optional[str] = None
    

class TenantUpdate(BaseModel):
    tenantId: str
    tenantName: Optional[str] = None
    apiKey: Optional[str] = None
    status: Optional[UserStatus] = None


class UserUpdate(BaseModel):
    username: str
    password: Optional[str] = None
    role: Optional[UserRole] = None
    name: Optional[str] = None
    tenantId: Optional[str] = None
    status: Optional[UserStatus] = None


class UserFilterRequest(BaseModel):
    id: Optional[str] = None 
    tenantId: Optional[str] = None
    status: Optional[UserStatus] = None
    role: Optional[UserRole] = None
    name: Optional[str] = None
    username: Optional[str] = None

class TenantFilterRequest(BaseModel):
    tenantName: Optional[str] = None  # Optional filter
    status: Optional[UserStatus] = None  # Optional filter


class StoreEditRequest(BaseModel):
    tenantId: str
    locationId: str
    storeId: str
    name: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    status: Optional[UserStatus] = None

class StoreDisableRequest(BaseModel):
    tenantId: str
    locationId: str
    storeId: str


class StoreFilterRequest(BaseModel):
    tenantId: Optional[str] = None
    locationId: Optional[str] = None
    storeId: Optional[str] = None
    status: Optional[UserStatus] = None


class LocationFilterRequest(BaseModel):
    tenantId: Optional[str] = None
    locationId: Optional[str] = None
    status: Optional[UserStatus] = None


class AddLocationRequest(BaseModel):
    tenantId: str
    locationId: str
    name: str
    status: UserStatus = UserStatus.ACTIVE


class AddStoreRequest(BaseModel):
    tenantId: str
    locationId: str
    storeId: str
    name: str
    state: Optional[str] = None
    country: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    status: UserStatus = UserStatus.ACTIVE


class UserResponse(BaseModel):
    id: str  
    username: str
    role: UserRole
    name: str
    status: UserStatus
    tenant_id: Optional[str] = None
    created_at: datetime
    created_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None

    class Config:
        orm_mode = True

class UpdateLocationRequest(BaseModel):
    tenantId: str
    locationId: str
    name: Optional[str] = None
    status: Optional[UserStatus] = None  # reuse your existing enum

class DisableLocationRequest(BaseModel):
    tenantId: str
    locationId: str