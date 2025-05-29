from collections import defaultdict
import pickle
from typing import Type
from odmantic import AIOEngine, Model
import json
import pandas as pd
import redis

from models.hepler import Product
from utils.file_download import download_file_from_s3


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


# def get_categories_from_cache_or_s3(tenant_id: str, location_id: str, s3_url: str, redis_client: redis.Redis):
#     redis_key = f"{tenant_id}:{location_id}:categories"

#     # Try Redis first
#     cached = redis_client.get(redis_key)
#     if cached:
#         print("✅ Loaded category data from Redis.")
#         # return json.loads(cached)
#         return json.loads(cached.decode("utf-8"))  # Decode bytes before json.loads

#     # Fallback to S3
#     file_buffer = download_file_from_s3(s3_url)
#     if file_buffer is None:
#         raise Exception("❌ Failed to fetch category file from S3.")

#     df = pd.read_csv(file_buffer)

#     # Build plain dictionary
#     categories_dct = {}
#     for _, row in df.iterrows():
#         product_name = str(row['Product_name']).strip().lower()
#         categories_dct[product_name] = {
#             "name": product_name,
#             "category": str(row['Category']).strip().lower(),
#             "subcategory": str(row['Subcategory']).strip().lower(),
#             "timing": str(row['Timing']).strip().lower()
#         }

#     # Store JSON in Redis
#     redis_client.set(redis_key, json.dumps(categories_dct))
#     print("✅ Stored category data in Redis (as JSON).")

#     return categories_dct


import json
import pandas as pd
import redis

def get_categories_from_cache_or_s3(tenant_id: str, location_id: str, s3_url: str, redis_client: redis.Redis):
    redis_key = f"{tenant_id}:{location_id}:categories"

    # Try Redis first
    cached = redis_client.get(redis_key)
    if cached:
        print("✅ Loaded category data from Redis.")
        # return json.loads(cached)
        return json.loads(cached.decode("utf-8"))  # Decode bytes before json.loads

    # Fallback to S3
    file_buffer = download_file_from_s3(s3_url)
    if file_buffer is None:
        raise Exception("❌ Failed to fetch category file from S3.")

    df = pd.read_csv(file_buffer)

    # Build plain dictionary
    categories_dct = {}
    for _, row in df.iterrows():
        product_name = str(row['Product_name']).strip().lower()
        categories_dct[product_name] = {
            "name": product_name,
            "category": str(row['Category']).strip().lower(),
            "subcategory": str(row['Subcategory']).strip().lower(),
            "timing": str(row['Timing']).strip().lower()
        }

    # Save to Redis as JSON
    redis_client.set(redis_key, json.dumps({k: v.to_dict() for k, v in categories_dct.items()}))
    print("Stored category data in Redis (as JSON).")

    # Convert before returning
    categories_dct = {
        p_name: Product.from_dict(data)
        for p_name, data in categories_dct.items()
    }
    return categories_dct
