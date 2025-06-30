# from loguru import logger
import pandas as pd
from singleton import category_cache_collection
from manager import settings
from category_classification import ClassificationService


GEMINI_PROJECT = settings.GEMINI_PROJECT
# logger.debug(GEMINI_PROJECT)
GEMINI_LOCATION = settings.GEMINI_LOCATION
# logger.debug(GEMINI_LOCATION)
GEMINI_SERVICE_ACCOUNT_PATH = settings.GEMINI_SERVICE_ACCOUNT_PATH
# logger.debug(GEMINI_SERVICE_ACCOUNT_PATH)



async def generate_category_df_from_processed(processed_df: pd.DataFrame, tenant_id: str, location_id: str):
    unique_products = (
        processed_df['Product_name']
        .dropna()
        .loc[lambda x: x != '']
        # .map(normalize_key)       # Normalize here before classify
        .unique()
        .tolist()
    )

    svc = ClassificationService(
        project=GEMINI_PROJECT,
        location=GEMINI_LOCATION,
        service_account_path=GEMINI_SERVICE_ACCOUNT_PATH
    )
    classified = svc.classify(unique_products)

    category_dict = {
        item.product: {
            "name": item.product,
            "category": item.category.strip().lower(),
            "subcategory": item.subcategory.strip().lower(),
            "timing": item.timing.value.strip().lower()
        }
        for item in classified
    }

    # Fetch existing document if any
    filter_query = {"tenant_id": tenant_id, "location_id": location_id}
    existing_doc = await category_cache_collection.find_one(filter_query)

    if existing_doc:
        existing_data = existing_doc.get("data", {})
        existing_data.update(category_dict)  # merge new data into existing
        await category_cache_collection.update_one(
            {"_id": existing_doc["_id"]},
            {"$set": {"data": existing_data}}
        )
    else:
        # Insert new document if not present
        document = {
            "tenant_id": tenant_id,
            "location_id": location_id,
            "data": category_dict
        }
        await category_cache_collection.insert_one(document)
    