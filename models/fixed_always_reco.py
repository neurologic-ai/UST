from enum import Enum
from odmantic import Model, Field
from datetime import datetime
from typing import List, Dict, Optional

class ProductType(str, Enum):
    fixed = "fixed"
    always = "always"

# === Model ===
class FixedProduct(Model):
    tenant_id: str
    location_id: str
    store_id: str
    products: List[Dict]
    created_at: datetime = datetime.utcnow()
    created_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None

class AlwaysRecommendProduct(Model):
    tenant_id: str
    location_id: str
    store_id: str
    products: List[Dict]
    created_at: datetime = datetime.utcnow()
    created_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
