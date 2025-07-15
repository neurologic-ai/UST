from enum import Enum
from odmantic import Model, Field
from datetime import datetime
from typing import List, Dict

class ProductType(str, Enum):
    fixed = "fixed"
    always = "always"

# === Model ===
from odmantic import Model, Field
from typing import List, Dict

class RecommendationConfig(Model):
    fixed_products: List[Dict] = Field(default_factory=list)
    always_recommend: List[Dict] = Field(default_factory=list)
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()
