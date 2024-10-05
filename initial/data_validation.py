import pandas as pd
from initial.constant import PROCESSED_DATA_PATH, GREEN, RED, RESET, EXPECTED_COLS

def validate():

    try:
        df = pd.read_csv(PROCESSED_DATA_PATH)
    except:
        print("Failed to read the dataset")
        return False

    problem = False
    for column, expected_dtype in EXPECTED_COLS.items():
        if column not in df.columns:
            print(f"{RED}Column '{column}' is missing.{RESET}")
            problem = True
        elif df[column].dtype != expected_dtype:
            print(f"{RED}Column '{column}' has incorrect type. Expected {expected_dtype} but got {df[column].dtype}.{RESET}")
            problem = True
        else:
            print(f"{GREEN}Column '{column}' exists and has the correct type ({expected_dtype}).{RESET}")

    if problem:
        return False
    else:
        print("Data Validation Successful")
        return True




