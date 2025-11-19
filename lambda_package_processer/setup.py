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
from typing import Dict, Any
from pymongo.errors import DuplicateKeyError

def build_lookup_dicts(df):
    df['UPC'] = df['UPC'].astype(str)
    name_to_upc = dict(zip(df['Product_name'], df['UPC']))
    upc_to_name = dict(zip(df['UPC'], df['Product_name']))
    return name_to_upc, upc_to_name

async def save_lookup_dicts(
    tenant_id: str,
    location_id: str,
    store_id: str,
    name_to_upc: Dict[Any, Any],
    upc_to_name: Dict[Any, Any],
):
    # Build per-key $set so the merge happens server-side atomically
    set_fields: Dict[str, Any] = {}

    # Merge into upc_to_name subdocument
    for upc, name in dict(upc_to_name).items():
        set_fields[f"upc_to_name.{upc}"] = name

    # Merge into name_to_upc subdocument
    for name, upc in dict(name_to_upc).items():
        set_fields[f"name_to_upc.{name}"] = upc

    if not set_fields:
        return  # nothing to write

    filt = {
        "tenant_id": tenant_id,
        "location_id": location_id,
        "store_id": store_id,
    }

    update_doc = {
        # Written only if the document is newly inserted (first time seen)
        "$setOnInsert": {
            "tenant_id": tenant_id,
            "location_id": location_id,
            "store_id": store_id,
        },
        # Merge/overwrite just the provided keys; others remain untouched
        "$set": set_fields,
    }

    try:
        # Classic update document (dict), compatible with Amazon DocumentDB
        await lookup_collection.update_one(filt, update_doc, upsert=True)
    except DuplicateKeyError:
        # Another writer inserted first; merge without upsert
        await lookup_collection.update_one(filt, {"$set": set_fields}, upsert=False)



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
        # group & upsert
        for store_id, df_store in df.groupby("store_id"):
            # IMPORTANT: Product_name should already be normalized before this function
            name_to_upc_map, upc_to_name_map = build_lookup_dicts(df_store)
            await save_lookup_dicts(tenant_id, location_id, store_id, name_to_upc_map, upc_to_name_map)

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

