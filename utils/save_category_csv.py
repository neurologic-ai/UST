import pandas as pd
import redis

from utils.make_category_csv import ClassificationService
from configs.manager import settings

API_KEY = settings.OPENAI_API_KEY

def generate_category_df_from_processed(processed_df: pd.DataFrame, redis_client: redis.Redis,) -> pd.DataFrame:
    processed_df['Product_name_clean'] = processed_df['Product_name'].str.strip().str.lower()
    # unique_products = processed_df['Product_name_clean'].dropna().unique().tolist()
    # Remove empty strings and NaNs
    unique_products = (
        processed_df['Product_name_clean']
        .dropna()
        .loc[lambda x: x != '']
        .unique()
        .tolist()
    )

    svc = ClassificationService(api_key=API_KEY,redis_client=redis_client)
    classified = svc.classify(unique_products)

    category_rows = [{
        "Product_name": item.product,
        "Category": item.category.value,
        "Subcategory": item.subcategory,
        "Timing": item.timing.value
    } for item in classified]

    return pd.DataFrame(category_rows)
