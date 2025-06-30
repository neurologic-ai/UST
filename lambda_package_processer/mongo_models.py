from typing import Dict
from odmantic import EmbeddedModel, Model


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