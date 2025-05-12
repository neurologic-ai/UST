import pandas as pd
from initialize.models import popular_based, association_based
from initialize.helper import insert_data, DataPreprocessor
from configs.constant import TIME_SLOTS, TIMINGS, PROCESSED_DATA_PATH, TIMINGS_COL
from db.singleton import \
breakfast_popular_collection_name, lunch_popular_collection_name, \
dinner_popular_collection_name, other_popular_collection_name, \
breakfast_association_collection_name, lunch_association_collection_name, \
dinner_association_collection_name, other_association_collection_name

import time

from utils.file_download import download_file_from_s3
from utils.helper import build_lookup_dicts, save_lookup_dicts


def run_models_and_store_outputs():
    # Download file from S3 and get a file-like object
    s3_url = ""
    processed_file_buffer = download_file_from_s3(s3_url)

    if processed_file_buffer is None:
        print("Failed to download file from S3.")
        return
    #Reading dataset
    try:
        df = pd.read_csv(processed_file_buffer)
    except FileNotFoundError:
        print(f"Error: File not found at {processed_file_buffer}. Please check the file path.")
        return
    except Exception as e:
        print(f"Error reading the dataset: {str(e)}")
        return
    
    #Pre-processing dataset
    preprocessor = DataPreprocessor(TIME_SLOTS)
    df = preprocessor.preprocess(df)

    name_to_upc_map, upc_to_name_map = build_lookup_dicts(df)
    save_lookup_dicts(name_to_upc_map, upc_to_name_map)
    for tm in TIMINGS:
        df_filtered = df[df[TIMINGS_COL] == tm].copy()
        # Apply Models
        popular_json = popular_based(df_filtered)
        association_json = association_based(df_filtered)

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