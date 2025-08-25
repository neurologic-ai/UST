from typing import Dict
from loguru import logger
import pandas as pd
import redis
from pymongo.errors import DuplicateKeyError, PyMongoError
from db.singleton import MongoDatabase
from models.db import CategoryCache, CategoryData
from utils.make_category_csv import ClassificationService
from configs.manager import settings
from db.singleton import category_cache_collection
GEMINI_PROJECT = settings.GEMINI_PROJECT
# logger.debug(GEMINI_PROJECT)
GEMINI_LOCATION = settings.GEMINI_LOCATION
# logger.debug(GEMINI_LOCATION)
GEMINI_SERVICE_ACCOUNT_PATH = settings.GEMINI_SERVICE_ACCOUNT_PATH
# logger.debug(GEMINI_SERVICE_ACCOUNT_PATH)


async def generate_category_df_from_processed(processed_df: pd.DataFrame, tenant_id: str, location_id: str):
    try:
        unique_products = (
            processed_df['Product_name']
            .dropna()
            .loc[lambda x: x != '']
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

        filter_query = {"tenant_id": tenant_id, "location_id": location_id}
        existing_doc = await category_cache_collection.find_one(filter_query)

        if existing_doc:
            existing_data = existing_doc.get("data", {})
            existing_data.update(category_dict)
            await category_cache_collection.update_one(
                {"_id": existing_doc["_id"]},
                {"$set": {"data": existing_data}}
            )
            logger.debug(f"Merged and updated category cache for tenant={tenant_id}, location={location_id}")

        else:
            document = {
                "tenant_id": tenant_id,
                "location_id": location_id,
                "data": category_dict
            }

            try:
                await category_cache_collection.insert_one(document)
                logger.debug(f"Inserted new category cache for tenant={tenant_id}, location={location_id}")
            except DuplicateKeyError:
                logger.warning(f"Duplicate key race for tenant={tenant_id}, location={location_id}, retrying with update.")
                try:
                    existing_doc = await category_cache_collection.find_one(filter_query)
                    if existing_doc:
                        existing_data = existing_doc.get("data", {})
                        existing_data.update(category_dict)
                        await category_cache_collection.update_one(
                            {"_id": existing_doc["_id"]},
                            {"$set": {"data": existing_data}}
                        )
                        logger.debug(f"Resolved conflict and updated category cache.")
                    else:
                        logger.warning(f"Document still not found on retry — skipping insert.")
                except Exception as inner_exc:
                    logger.exception(f"Error during retry update after duplicate key: {inner_exc}")

    except Exception as e:
        logger.exception(f"generate_category_df_from_processed failed for tenant={tenant_id}, location={location_id}: {e}")