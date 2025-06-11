from loguru import logger
import pandas as pd
import redis

from utils.make_category_csv import ClassificationService
from configs.manager import settings

GEMINI_PROJECT = settings.GEMINI_PROJECT
logger.debug(GEMINI_PROJECT)
GEMINI_LOCATION = settings.GEMINI_LOCATION
logger.debug(GEMINI_LOCATION)
GEMINI_SERVICE_ACCOUNT_PATH = settings.GEMINI_SERVICE_ACCOUNT_PATH
logger.debug(GEMINI_SERVICE_ACCOUNT_PATH)

# def generate_category_df_from_processed(processed_df: pd.DataFrame, redis_client: redis.Redis,) -> pd.DataFrame:
#     # processed_df['Product_name_clean'] = processed_df['Product_name'].str.strip().str.lower()
#     # unique_products = processed_df['Product_name_clean'].dropna().unique().tolist()
#     # Remove empty strings and NaNs
#     unique_products = (
#         processed_df['Product_name']
#         .dropna()
#         .loc[lambda x: x != '']
#         .unique()
#         .tolist()
#     )

#     svc = ClassificationService(api_key=API_KEY,redis_client=redis_client)
#     classified = svc.classify(unique_products)

#     category_rows = [{
#         "Product_name": item.product,
#         "Category": item.category,
#         "Subcategory": item.subcategory,
#         "Timing": item.timing.value
#     } for item in classified]

#     return pd.DataFrame(category_rows)


def generate_category_df_from_processed(processed_df: pd.DataFrame, redis_client: redis.Redis,) -> pd.DataFrame:
# def generate_category_df_from_processed(processed_df: pd.DataFrame) -> pd.DataFrame:
    # Normalize product names: strip, lower, remove special spaces, etc.
    def normalize_key(name: str) -> str:
        if not isinstance(name, str):
            return ""
        return name.replace('\xa0', ' ').strip().lower()

    # Get unique normalized product names
    unique_products = (
        processed_df['Product_name']
        .dropna()
        .loc[lambda x: x != '']
        .map(normalize_key)       # Normalize here before classify
        .unique()
        .tolist()
    )

    svc = ClassificationService(
        project=GEMINI_PROJECT,
        location=GEMINI_LOCATION,
        service_account_path=GEMINI_SERVICE_ACCOUNT_PATH,
        redis_client=redis_client
    )
    classified = svc.classify(unique_products)

    category_rows = [{
        "Product_name": normalize_key(item.product),  # Normalize again before saving
        "Category": item.category,
        "Subcategory": item.subcategory,
        "Timing": item.timing.value
    } for item in classified]

    return pd.DataFrame(category_rows)
