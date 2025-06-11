from collections import defaultdict
import pickle
from typing import Type
from odmantic import AIOEngine, Model
import json
import pandas as pd
import redis

from models.hepler import Product
from utils.file_download import download_file_from_s3
from utils.make_category_csv import normalize_key


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


# import json
# import pandas as pd
# import redis
# from models.hepler import Product  # Ensure correct import path
# from utils.file_download import download_file_from_s3  # Ensure correct import path

# def get_categories_from_cache_or_s3(tenant_id: str, location_id: str, s3_url: str, redis_client: redis.Redis):
#     redis_key = f"{tenant_id}:{location_id}:categories"

#     # ✅ 1. Try Redis first
#     cached = redis_client.get(redis_key)
#     if cached:
#         print("✅ Loaded category data from Redis.")

#         # Decode and parse
#         data = json.loads(cached.decode("utf-8"))

#         # Convert each item back to Product object
#         categories_dct = {
#             name: Product.from_dict(prod_dict)
#             for name, prod_dict in data.items()
#         }
#         return categories_dct

#     # ❌ 2. Fallback to S3 if Redis miss
#     print("⚠️  Cache miss. Loading category data from S3...")
#     file_buffer = download_file_from_s3(s3_url)
#     if file_buffer is None:
#         raise Exception("❌ Failed to fetch category file from S3.")

#     df = pd.read_csv(file_buffer)

#     # ✅ 3. Build dictionary of Product objects
#     categories_dct = {}
#     for _, row in df.iterrows():
#         product_name = normalize_key(row['Product_name'])  # << ✅ robust normalization
#         categories_dct[product_name] = Product(
#             name=product_name,
#             category=str(row['Category']).strip().lower(),
#             subcategory=str(row['Subcategory']).strip().lower(),
#             timing=str(row['Timing']).strip().lower()
#         )

#     # ✅ 4. Cache the dictionary as JSON
#     redis_client.set(
#         redis_key,
#         json.dumps({k: v.to_dict() for k, v in categories_dct.items()})
#     )
#     print("✅ Stored category data in Redis.")

#     return categories_dct



# ####

# def exclude_obvious_categories(self):
#         """Remove products from excluded subcategories (skip missing keys)."""
#         def is_valid(p):
#             cleaned = p.strip().replace('\xa0', ' ')
#             cat = self.categories.get(cleaned)
#             return cat and cat.subcategory not in self.excluded_subcategories

#         self.reco_list = [p for p in self.reco_list if is_valid(p)]


# import os
# import json
# import pandas as pd

# def get_categories_from_cache_or_s3(tenant_id: str, location_id: str, s3_url: str):
#     # Define a local cache path
#     cache_dir = "local_cache"
#     os.makedirs(cache_dir, exist_ok=True)

#     cache_file = os.path.join(cache_dir, f"{tenant_id}_{location_id}_categories.json")

#     # ✅ 1. Try loading from local cache
#     if os.path.exists(cache_file):
#         print("✅ Loaded category data from local cache.")

#         with open(cache_file, "r", encoding="utf-8") as f:
#             data = json.load(f)

#         # Convert dict to Product objects
#         categories_dct = {
#             name: Product.from_dict(prod_dict)
#             for name, prod_dict in data.items()
#         }
#         return categories_dct

#     # ❌ 2. Fallback to S3 if cache miss
#     print("⚠️  Cache miss. Loading category data from S3...")
#     file_buffer = download_file_from_s3(s3_url)
#     if file_buffer is None:
#         raise Exception("❌ Failed to fetch category file from S3.")

#     df = pd.read_csv(file_buffer)

#     # ✅ 3. Build dictionary of Product objects
#     categories_dct = {}
#     for _, row in df.iterrows():
#         product_name = normalize_key(row['Product_name'])
#         categories_dct[product_name] = Product(
#             name=product_name,
#             category=str(row['Category']).strip().lower(),
#             subcategory=str(row['Subcategory']).strip().lower(),
#             timing=str(row['Timing']).strip().lower()
#         )

#     # ✅ 4. Save the dictionary as local JSON
#     with open(cache_file, "w", encoding="utf-8") as f:
#         json.dump({k: v.to_dict() for k, v in categories_dct.items()}, f, ensure_ascii=False, indent=2)

#     print("✅ Stored category data in local cache.")

#     return categories_dct

# import json
# import pandas as pd

# def get_categories_from_cache_or_s3(tenant_id: str, location_id: str, s3_url: str, mongo_collection):
#     cache_key = f"{tenant_id}:{location_id}"

#     # ✅ 1. Try loading from MongoDB
#     doc = mongo_collection.find_one({"_id": cache_key})
#     if doc and "data" in doc:
#         print("✅ Loaded category data from MongoDB.")
#         data = doc["data"]

#         # Convert dict to Product objects
#         categories_dct = {
#             name: Product.from_dict(prod_dict)
#             for name, prod_dict in data.items()
#         }
#         return categories_dct

#     # ❌ 2. Fallback to S3 if MongoDB miss
#     print("⚠️  Cache miss. Loading category data from S3...")
#     file_buffer = download_file_from_s3(s3_url)
#     if file_buffer is None:
#         raise Exception("❌ Failed to fetch category file from S3.")

#     df = pd.read_csv(file_buffer)

#     # ✅ 3. Build dictionary of Product objects
#     categories_dct = {}
#     for _, row in df.iterrows():
#         product_name = normalize_key(row['Product_name'])
#         categories_dct[product_name] = Product(
#             name=product_name,
#             category=str(row['Category']).strip().lower(),
#             subcategory=str(row['Subcategory']).strip().lower(),
#             timing=str(row['Timing']).strip().lower()
#         )

#     # ✅ 4. Save to MongoDB
#     mongo_collection.replace_one(
#         {"_id": cache_key},
#         {"_id": cache_key, "data": {k: v.to_dict() for k, v in categories_dct.items()}},
#         upsert=True
#     )
#     print("✅ Stored category data in MongoDB.")

#     return categories_dct


import pandas as pd
from typing import Dict
from models.db import CategoryCache, CategoryData  # Adjust as needed

async def get_categories_from_cache_or_s3(tenant_id: str, location_id: str, s3_url: str, db) -> Dict[str, "Product"]:
    # 1. Try MongoDB
    # cache_doc = CategoryCache.find_one({
    #     "tenant_id": tenant_id,
    #     "location_id": location_id
    # })
    cache_key = {"tenant_id": tenant_id, "location_id": location_id}
    cache_doc = await db.find_one(CategoryCache, cache_key)
    if cache_doc:
        print("✅ Loaded category data from MongoDB.")

        categories_dct = {
            name: Product.from_dict({
                "name": data.name,
                "category": data.category,
                "subcategory": data.subcategory,
                "timing": data.timing
            })
            for name, data in cache_doc.data.items()
        }
        return categories_dct

    # 2. Fallback to S3
    print("⚠️  Cache miss. Loading category data from S3...")
    file_buffer = download_file_from_s3(s3_url)
    if file_buffer is None:
        raise Exception("❌ Failed to fetch category file from S3.")

    df = pd.read_csv(file_buffer)

    categories_dct = {}
    embedded_data = {}
    for _, row in df.iterrows():
        product_name = normalize_key(row['Product_name'])

        # Product for use in memory
        categories_dct[product_name] = Product(
            name=product_name,
            category=str(row['Category']).strip().lower(),
            subcategory=str(row['Subcategory']).strip().lower(),
            timing=str(row['Timing']).strip().lower()
        )

        # EmbeddedModel for DB
        embedded_data[product_name] = CategoryData(
            name=product_name,
            category=categories_dct[product_name].category,
            subcategory=categories_dct[product_name].subcategory,
            timing=categories_dct[product_name].timing
        )

    # 3. Save to MongoDB
    category_cache = CategoryCache(
        tenant_id=tenant_id,
        location_id=location_id,
        data=embedded_data
    )
    await db.save(category_cache)

    print("✅ Stored category data in MongoDB.")
    return categories_dct
