from pydantic import BaseModel
from typing import List
from bson import ObjectId
from mongoengine import  ListField, DictField


class InputData(BaseModel):
    cart_items: List

def to_serializable(doc):
    """Convert MongoDB ObjectId to string."""
    if isinstance(doc, ObjectId):
        return str(doc)
    return doc