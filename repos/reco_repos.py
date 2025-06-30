from typing import Type
from loguru import logger
from odmantic import AIOEngine, Model
from models.hepler import Product
from typing import Dict
from models.db import CategoryCache


async def get_product_names_from_upcs(
    db: AIOEngine,
    upcs: list[str],
    model: Type[Model],
    filters: dict
) -> list[str]:
    document = await db.find_one(model, filters)
    if not document:
        return []

    popular_data = document.popular_data
    upc_to_name = {
        v['upc']: name for name, v in popular_data.items()
        if 'upc' in v and 'count' in v
    }
    return [upc_to_name[upc] for upc in upcs if upc in upc_to_name]


async def get_categories_from_cache_or_s3(tenant_id: str, location_id: str, s3_url: str, db) -> Dict[str, "Product"]:
    cache_filter = {"tenant_id": tenant_id, "location_id": location_id}
    cursor = db.find(CategoryCache, cache_filter)

    categories_dct: Dict[str, Product] = {}

    async for doc in cursor:
        if not doc.data:
            continue
        for name, data in doc.data.items():
            categories_dct[name] = Product.from_dict({
                "name": data.name,
                "category": data.category,
                "subcategory": data.subcategory,
                "timing": data.timing
            })

    if categories_dct:
        return categories_dct

    return {}
    