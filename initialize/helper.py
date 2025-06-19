import traceback
import numpy as np
import pandas as pd
from configs.constant import DATE_COL, PRODUCT_NAME_COL, TIMINGS_COL, TIMINGS
from typing import Union, Dict, Tuple
from db.singleton import lookup_collection


def get_timing(hr, timing_ranges):
    try:
        for category, (start, end) in timing_ranges.items():
                    if category in TIMINGS:
                    # Handles cases where the range spans midnight
                        if start <= hr < end or (start > end and (hr >= start or hr < end)):
                            return category
    except:
        return "None"


def vectorized_apply_timing_classification(df: pd.DataFrame, datetime_col: str, output_col: str, timing_ranges: Dict[str, Tuple[int, int]]) -> pd.DataFrame:
    df[datetime_col] = pd.to_datetime(df[datetime_col], errors='coerce')
    df['hour'] = df[datetime_col].dt.hour

    def get_category_series(hours: pd.Series) -> pd.Series:
        result = pd.Series(["None"] * len(hours), index=hours.index)

        for category, (start, end) in timing_ranges.items():
            if category not in TIMINGS:
                continue
            if start <= end:
                mask = (hours >= start) & (hours < end)
            else:  # spans midnight
                mask = (hours >= start) | (hours < end)
            result[mask] = category
        return result

    df[output_col] = get_category_series(df['hour'])
    df.drop(columns=['hour'], inplace=True)
    return df


class TimingClassifier:
    def __init__(self, timing_ranges: Dict[str, Tuple[int, int]]):
        """
        Initialize the TimingClassifier with specific timing ranges.
        :param timing_ranges: A dictionary of timing categories and their hour ranges.
        """
        self.timing_ranges = timing_ranges

    def classify_timing(self, datetime_str: Union[str, pd.Timestamp]) -> str:
        """
        Classify the timing based on the given datetime string or timestamp.
        :param datetime_str: A datetime string or pd.Timestamp to classify.
        :return: The corresponding timing category or "None" if invalid.
        """
        try:
            dt = pd.to_datetime(datetime_str, errors='coerce')
            if pd.isnull(dt):
                return "None"
            hour = dt.hour
            category = get_timing(hour, self.timing_ranges)
            return category

        except Exception:
            return "None"

    # def apply_timing_classification(self, df: pd.DataFrame, datetime_col: str, output_col: str) -> pd.DataFrame:
    #     """
    #     Apply timing classification to a DataFrame.
    #     :param df: Input DataFrame.
    #     :param datetime_col: Column name in DataFrame containing datetime strings.
    #     :param output_col: Column name where the classified timings will be stored.
    #     :return: Updated DataFrame with the timing classification.
    #     """
    #     df[output_col] = df[datetime_col].apply(self.classify_timing)
    #     return df

    

class DataPreprocessor:
    def __init__(self, timing_slots: Dict[str, Tuple[int, int]]):
        """
        Initialize the DataPreprocessor with specific timing slots for classification.
        :param timing_slots: A dictionary of timing categories and their hour ranges.
        """
        self.timing_classifier = TimingClassifier(timing_slots)

    def preprocess(self, df_inp: pd.DataFrame) -> pd.DataFrame:
        """
        Preprocess the DataFrame by cleaning and classifying timing.
        :param df_inp: Input DataFrame.
        :return: Processed DataFrame with cleaned and classified timing.
        """
        # Clean the 'Product_name' column
        if PRODUCT_NAME_COL in df_inp.columns:
            df_inp[PRODUCT_NAME_COL] = df_inp[PRODUCT_NAME_COL].apply(lambda x: x.strip().lower() if isinstance(x, str) else x)

        # Apply timing classification
        # df_out = self.timing_classifier.apply_timing_classification(df_inp, datetime_col = DATE_COL, output_col = TIMINGS_COL)
        df_out = vectorized_apply_timing_classification(
            df_inp,
            datetime_col=DATE_COL,
            output_col=TIMINGS_COL,
            timing_ranges=self.timing_classifier.timing_ranges
        )
        return df_out
    


# def insert_data(collection_name, inp_data, many = True, dataset_name = ''):
#     collection_name.delete_many({})
#     if many:
#         collection_name.insert_many(inp_data)
#     else:
#         collection_name.insert_one(inp_data)
#     print(f"{dataset_name} data stored successfully!")

import numpy as np

def convert_numpy_to_native(obj):
    """Recursively convert numpy types to native Python types."""
    if isinstance(obj, dict):
        return {k: convert_numpy_to_native(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_to_native(i) for i in obj]
    elif isinstance(obj, (np.integer, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64)):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    else:
        return obj

# def insert_data(collection_name, inp_data, many=True, dataset_name=''):
#     # Convert numpy types to native Python types
#     if many:
#         inp_data = [convert_numpy_to_native(doc) for doc in inp_data]
#     else:
#         inp_data = convert_numpy_to_native(inp_data)

#     # Clear existing data for the combination of store_id, location_id, and timing
#     filter_query = {
#         "location_id": inp_data[0].get("location_id") if many else inp_data.get("location_id"),
#         "store_id": inp_data[0].get("store_id") if many else inp_data.get("store_id")
#     }
#     collection_name.delete_many(filter_query)

#     # Insert new data
#     if many:
#         collection_name.insert_many(inp_data)
#     else:
#         collection_name.insert_one(inp_data)

#     print(f"{dataset_name} data stored successfully!")

async def insert_data(collection_name, inp_data, many=True, dataset_name=''):
    print("DEBUG: Type of collection_name:", type(collection_name))
    # Convert numpy types to native Python types
    if many:
        inp_data = [convert_numpy_to_native(doc) for doc in inp_data]
    else:
        inp_data = convert_numpy_to_native(inp_data)

    # Clear existing data for the combination of store_id and location_id
    filter_query = {
        "location_id": inp_data[0].get("location_id") if many else inp_data.get("location_id"),
        "store_id": inp_data[0].get("store_id") if many else inp_data.get("store_id")
    }

    print("Deleting existing data with filter:", filter_query)

    try:
        result = await collection_name.delete_many(filter_query)  # await here
        print(f"Deleted {result.deleted_count} existing records")
    except Exception as e:
        print("Deletion failed:", e)

    # print("Final data going to DB:", inp_data)

    try:
        if many:
            result = await collection_name.insert_many(inp_data)  
            print(result.acknowledged)
            # print(f"Insertion successful, inserted IDs: {result.inserted_ids}")
        else:
            result = await collection_name.insert_one(inp_data)  
            print(result.acknowledged)
            # print(f"Insertion successful, inserted ID: {result.inserted_id}")
        print(f"{dataset_name} data stored successfully!")
    except Exception as e:
        print("Insertion failed:", e)
        traceback.print_exc()



async def load_lookup_dicts(tenant_id, location_id):
    doc = await lookup_collection.find_one({
        "tenant_id": tenant_id,
        "location_id": location_id
    })

    if doc:
        return doc.get("name_to_upc", {}), doc.get("upc_to_name", {})
    else:
        return {}, {}
