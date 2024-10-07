from pydantic import BaseModel
from typing import List
from bson import ObjectId


class RecommendationRequestBody(BaseModel):
    cart_items: List
    current_hr: int
    current_dayofweek: int
    current_weather_category: str
    current_holiday: str
    top_n: int

def to_serializable(doc):
    """Convert MongoDB ObjectId to string."""
    if isinstance(doc, ObjectId):
        return str(doc)
    return doc