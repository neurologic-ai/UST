import pandas as pd

from utils.make_category_csv import ClassificationService
from configs.manager import settings

API_KEY = settings.OPENAI_API_KEY

def generate_category_df_from_processed(processed_df: pd.DataFrame) -> pd.DataFrame:
    processed_df['Product_name_clean'] = processed_df['Product_name'].str.strip().str.lower()
    unique_products = processed_df['Product_name_clean'].dropna().unique().tolist()

    svc = ClassificationService(api_key=API_KEY)
    classified = svc.classify(unique_products)

    category_rows = [{
        "Product_name": item.product,
        "Category": item.category.value,
        "Subcategory": "N/A",
        "Timing": item.timing.value
    } for item in classified]

    return pd.DataFrame(category_rows)
