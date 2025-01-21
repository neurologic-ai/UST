import pandas as pd
from configs.constant import DATE_COL, PRODUCT_NAME_COL, TIMINGS_COL, TIMINGS
from typing import Union, Dict, Tuple


def get_timing(hr, timing_ranges):
    try:
        for category, (start, end) in timing_ranges.items():
                    if category in TIMINGS:
                    # Handles cases where the range spans midnight
                        if start <= hr < end or (start > end and (hr >= start or hr < end)):
                            return category
    except:
        return "None"

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

    def apply_timing_classification(self, df: pd.DataFrame, datetime_col: str, output_col: str) -> pd.DataFrame:
        """
        Apply timing classification to a DataFrame.
        :param df: Input DataFrame.
        :param datetime_col: Column name in DataFrame containing datetime strings.
        :param output_col: Column name where the classified timings will be stored.
        :return: Updated DataFrame with the timing classification.
        """
        df[output_col] = df[datetime_col].apply(self.classify_timing)
        return df

    

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
        df_out = self.timing_classifier.apply_timing_classification(df_inp, datetime_col = DATE_COL, output_col = TIMINGS_COL)
        return df_out
    


def insert_data(collection_name, inp_data, many = True, dataset_name = ''):
    collection_name.delete_many({})
    if many:
        collection_name.insert_many(inp_data)
    else:
        collection_name.insert_one(inp_data)
    print(f"{dataset_name} data stored successfully!")