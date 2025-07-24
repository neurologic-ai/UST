from enum import Enum
from odmantic import Model, Field
from datetime import datetime
from typing import List, Dict, Optional

class ProductType(str, Enum):
    fixed = "fixed"
    always = "always"

# === Model ===
class FixedProduct(Model):
    products: List[Dict]
    created_at: datetime = datetime.utcnow()
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None

class AlwaysRecommendProduct(Model):
    products: List[Dict]
    created_at: datetime = datetime.utcnow()
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
