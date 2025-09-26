from typing import List, Type
from loguru import logger
from odmantic import AIOEngine, Model
from models.hepler import Product
from typing import Dict
from models.db import CategoryCache
import pandas as pd
from fastapi import UploadFile, HTTPException


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


async def get_categories_from_cache_or_s3(tenant_id: str, location_id: str, db) -> Dict[str, "Product"]:
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


async def validate_csv_columns(file: UploadFile, required_columns: list[str]):
    try:
        # Use file stream directly without reading full content
        file.file.seek(0)
        df = pd.read_csv(file.file, nrows=0)  # Only reads header
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read CSV header: {str(e)}")

    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required columns: {', '.join(missing)}"
        )

    
async def get_categories_for_products(
    product_names: List[str],
    tenant_id: str,
    location_id: str,
    store_id: str,     # ✅ NEW
    db
) -> Dict[str, Product]:
    """
    Returns category metadata only for the given list of product names, scoped to a single store.
    """
    cache_filter = {
        "tenant_id": tenant_id,
        "location_id": location_id,
        "store_id": store_id,   # ✅ scope by store
    }
    cursor = db.find(CategoryCache, cache_filter)

    name_set = set(p.strip() for p in product_names if p)
    categories_dct: Dict[str, Product] = {}

    async for doc in cursor:
        if not doc.data:
            continue
        for name, data in doc.data.items():
            key = name.strip()
            if key in name_set:
                categories_dct[key] = Product.from_dict({
                    "name": data.name,
                    "category": data.category,
                    "subcategory": data.subcategory,
                    "timing": data.timing
                })
                if len(categories_dct) == len(name_set):
                    return categories_dct  # Early exit if all found

    return categories_dct