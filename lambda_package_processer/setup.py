import asyncio
import traceback
from loguru import logger
import pandas as pd
# from models import popular_based, association_based
from helper import insert_association_items_dict_style, DataPreprocessor, insert_popular_items_dict_style
from constant import TIME_SLOTS, TIMINGS, TIMINGS_COL
from model import association_based, popular_based
from singleton import \
breakfast_popular_collection_name, lunch_popular_collection_name, \
dinner_popular_collection_name, other_popular_collection_name, \
breakfast_association_collection_name, lunch_association_collection_name, \
dinner_association_collection_name, other_association_collection_name, lookup_collection

def build_lookup_dicts(df):
    df['UPC'] = df['UPC'].astype(str)
    name_to_upc = dict(zip(df['Product_name'], df['UPC']))
    upc_to_name = dict(zip(df['UPC'], df['Product_name']))
    return name_to_upc, upc_to_name

async def save_lookup_dicts(tenant_id, location_id, name_to_upc, upc_to_name):
    try:
        # Fetch existing doc
        existing = await lookup_collection.find_one({"tenant_id": tenant_id, "location_id": location_id}) or {}

        # Merge into existing
        merged_name_to_upc = {**existing.get("name_to_upc", {}), **name_to_upc}
        merged_upc_to_name = {**existing.get("upc_to_name", {}), **upc_to_name}

        # Build merged doc
        lookup_doc = {
            "tenant_id": tenant_id,
            "location_id": location_id,
            "name_to_upc": merged_name_to_upc,
            "upc_to_name": merged_upc_to_name
        }

        # Upsert with full merged doc
        lookup_collection.update_one(
            {"tenant_id": tenant_id, "location_id": location_id},
            {"$set": lookup_doc},
            upsert=True
        )

    except Exception as e:
        logger.debug("❌ Failed to merge lookup_collection")
        logger.debug(traceback.format_exc())
        raise


# Mapping for time slots to collection names
COLLECTION_MAPPING = {
    "Breakfast": (breakfast_popular_collection_name, breakfast_association_collection_name),
    "Lunch": (lunch_popular_collection_name, lunch_association_collection_name),
    "Dinner": (dinner_popular_collection_name, dinner_association_collection_name),
    "Other": (other_popular_collection_name, other_association_collection_name),
}

async def process_time_slot(tm, df_filtered, tenant_id):
    try:
        logger.debug(f"Processing {tm} recommendation dataset...")

        popular_json = popular_based(df_filtered, tenant_id)
        association_json = association_based(df_filtered, tenant_id)

        pop_coll, assoc_coll = COLLECTION_MAPPING[tm]

        await asyncio.gather(
            insert_popular_items_dict_style(pop_coll, popular_json),
            insert_association_items_dict_style(assoc_coll, association_json)
        )

        logger.debug(f"{tm} Popular and Association Saved in Mongo")
    except Exception as e:
        logger.debug(f"❌ Error in processing {tm} data: {str(e)}")
        logger.debug(traceback.format_exc())



async def run_models_and_store_outputs(tenant_id, location_id, df: pd.DataFrame = None):
    logger.debug("Inside run_models_and_store_outputs")
    try:
        if df is None:
            logger.debug("Error: Dataframe must be provided.")
            return 

        #Pre-processing dataset
        preprocessor = DataPreprocessor(TIME_SLOTS)
        df = preprocessor.preprocess(df)
        logger.debug("Preprocessing Done")
            # Build and save lookup dictionaries
        name_to_upc_map, upc_to_name_map = build_lookup_dicts(df)
        await save_lookup_dicts(tenant_id, location_id, name_to_upc_map, upc_to_name_map)
        logger.debug("look_up Dict Saved in Mongo")
        tasks = []
        for tm in TIMINGS:
            df_filtered = df[df[TIMINGS_COL] == tm].copy()
            tasks.append(process_time_slot(tm, df_filtered, tenant_id))

        await asyncio.gather(*tasks)
        logger.debug("✅ All data saved in Mongo")
        
    except Exception as e:
        logger.debug(f"Error occurred: {str(e)}")
        logger.debug(f"Full traceback:\n{traceback.format_exc()}")
