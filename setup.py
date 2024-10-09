import pandas as pd
from initial.data_validation import validate
from initial.models import popular_based, time_based, calendar_based, association_based, weather_based
from initial.constant import PROCESSED_DATA_PATH
from utils.helper import insert_data
from db.singleton import popular_collection_name, time_collection_name, weather_collection_name, calendar_collection_name, association_collection_name


def run_models_and_store_outputs():
    validation = validate()
    if not validation:
        print(f"Error: Validation failed, please try again later with correct data format.")
        return 
    try:
        df = pd.read_csv(PROCESSED_DATA_PATH)
    except FileNotFoundError:
        print(f"Error: File not found at {PROCESSED_DATA_PATH}. Please check the file path.")
        return
    except Exception as e:
        print(f"Error reading the dataset: {str(e)}")
        return

    # Popular-based recommendation
    try:
        print("Preparing popular based recommendation dataset...")
        json_data = popular_based(df)
        insert_data(popular_collection_name, json_data, dataset_name = 'Popular')
    except Exception as e:
        print(f"Error in preparing or inserting popular-based recommendation data: {str(e)}")
        return

    # Time-based recommendation
    try:
        print("Preparing time based recommendation dataset...")
        json_data = time_based(df)
        insert_data(time_collection_name, json_data, dataset_name = 'Time')
    except Exception as e:
        print(f"Error in preparing or inserting time-based recommendation data: {str(e)}")
        return

    # Weather-based recommendation
    try:
        print("Preparing weather based recommendation dataset...")
        json_data = weather_based(df)
        insert_data(weather_collection_name, json_data, dataset_name = 'Weather')
    except Exception as e:
        print(f"Error in preparing or inserting weather-based recommendation data: {str(e)}")
        return 

    # Calendar-based recommendation
    try:
        print("Preparing calendar based recommendation dataset...")
        json_data = calendar_based(df)
        insert_data(calendar_collection_name, json_data, dataset_name = 'Calendar')
    except Exception as e:
        print(f"Error in preparing or inserting calendar-based recommendation data: {str(e)}")
        return

    # Association-based recommendation
    try:
        print("Preparing association based recommendation dataset...")
        json_data = association_based(df)
        insert_data(association_collection_name, json_data, dataset_name = 'Association')
    except Exception as e:
        print(f"Error in preparing or inserting association-based recommendation data: {str(e)}")
        return

run_models_and_store_outputs()