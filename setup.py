import traceback
import pandas as pd
from initialize.models import popular_based, association_based
from initialize.helper import insert_data, DataPreprocessor
from configs.constant import TIME_SLOTS, TIMINGS, PROCESSED_DATA_PATH, TIMINGS_COL
from db.singleton import \
breakfast_popular_collection_name, lunch_popular_collection_name, \
dinner_popular_collection_name, other_popular_collection_name, \
breakfast_association_collection_name, lunch_association_collection_name, \
dinner_association_collection_name, other_association_collection_name, lookup_collection
from loguru import logger
import time

from utils.file_download import download_file_from_s3

# def build_lookup_dicts(df):
#     name_to_upc = dict(zip(df['Product_name'], df['UPC']))
#     upc_to_name = dict(zip(df['UPC'], df['Product_name']))
#     return name_to_upc, upc_to_name

def build_lookup_dicts(df):
    name_to_upc = dict(zip(df['Product_name'], df['UPC']))

    # Convert UPC keys to string
    upc_to_name = {str(k): v for k, v in zip(df['UPC'], df['Product_name'])}

    return name_to_upc, upc_to_name


def save_lookup_dicts(tenant_id, location_id, name_to_upc, upc_to_name):
    lookup_doc = {
        "tenant_id": tenant_id,
        "location_id": location_id,
        "name_to_upc": name_to_upc,
        "upc_to_name": upc_to_name
    }
    try:
        lookup_collection.update_one(
            {"tenant_id": tenant_id, "location_id": location_id},
            {"$set": lookup_doc},
            upsert=True
        )
    except Exception as e:
        logger.debug("❌ Failed to update lookup_collection. Document:")
        logger.debug(lookup_doc)
        logger.debug(traceback.format_exc())
        raise




def run_models_and_store_outputs(s3_url, tenant_id, location_id):
    # Download file from S3 and get a file-like object
    processed_file_buffer = download_file_from_s3(s3_url)

    if processed_file_buffer is None:
        print("Failed to download file from S3.")
        return
    #Reading dataset
    try:
        processed_file_buffer.seek(0)
        print("Buffer preview:", processed_file_buffer.read(1000))  # preview 1000 bytes
        processed_file_buffer.seek(0)

        df = pd.read_csv(processed_file_buffer, dtype={"UPC": str, "store_id": str})
    except FileNotFoundError:
        print(f"Error: File not found at {processed_file_buffer}. Please check the file path.")
        return
    except Exception as e:
        print(f"Error reading the dataset: {str(e)}")
        return
    
        # Build and save lookup dictionaries
    name_to_upc_map, upc_to_name_map = build_lookup_dicts(df)
    save_lookup_dicts(tenant_id, location_id, name_to_upc_map, upc_to_name_map)
    
    #Pre-processing dataset
    preprocessor = DataPreprocessor(TIME_SLOTS)
    df = preprocessor.preprocess(df)


    for tm in TIMINGS:
        df_filtered = df[df[TIMINGS_COL] == tm].copy()
        # Apply Models
        popular_json = popular_based(df_filtered,tenant_id)
        association_json = association_based(df_filtered, tenant_id)

        # Storing breakfast data
        if tm == 'Breakfast':
            try:
                print("Preparing breakfast recommendation dataset...")
                insert_data(breakfast_popular_collection_name, popular_json, dataset_name = 'breakfast_popular')
                time.sleep(1)
                insert_data(breakfast_association_collection_name, association_json, dataset_name = 'breakfast_association')
                time.sleep(1)
            except Exception as e:
                print(f"Error in preparing or inserting breakfast recommendation data: {str(e)}")
                return
            
        # Storing Lunch data
        elif tm == 'Lunch':
            try:
                print("Preparing lunch recommendation dataset...")
                insert_data(lunch_popular_collection_name, popular_json, dataset_name = 'lunch_popular')
                time.sleep(1)
                insert_data(lunch_association_collection_name, association_json, dataset_name = 'lunch_association')
                time.sleep(1)
            except Exception as e:
                print(f"Error in preparing or inserting lunch recommendation data: {str(e)}")
                return
        
        # Storing Dinner data
        elif tm == 'Dinner':
            try:
                print("Preparing dinner recommendation dataset...")
                insert_data(dinner_popular_collection_name, popular_json, dataset_name = 'dinner_popular')
                time.sleep(1)
                insert_data(dinner_association_collection_name, association_json, dataset_name = 'dinner_association')
                time.sleep(1)
            except Exception as e:
                print(f"Error in preparing or inserting dinner recommendation data: {str(e)}")
                return
            
        # Storing Other data
        elif tm == 'Other':
            try:
                print("Preparing other recommendation dataset...")
                insert_data(other_popular_collection_name, popular_json, dataset_name = 'other_popular')
                time.sleep(1)
                insert_data(other_association_collection_name, association_json, dataset_name = 'other_association')
                time.sleep(1)
            except Exception as e:
                print(f"Error in preparing or inserting other recommendation data: {str(e)}")
                return

# run_models_and_store_outputs() # Need to remove this, only for testing