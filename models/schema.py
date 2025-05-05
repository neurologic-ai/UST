from pydantic import BaseModel
from typing import List
from bson import ObjectId
from typing import Any


class RecommendationRequestBody(BaseModel):
    cartItems: list[str]
    topN: int
    currentHour: int
    storeId: int
    locationId: int

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