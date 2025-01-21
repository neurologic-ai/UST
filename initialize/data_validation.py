from configs.constant import  GREEN, RED, RESET, EXPECTED_PROCESSED_COLS, EXPECTED_CATEGORY_COLS

def validate(df1, df2):
    problem = False
    for column, expected_dtype in EXPECTED_PROCESSED_COLS.items():
        if column not in df1.columns:
            print(f"{RED}Column '{column}' is missing.{RESET}")
            problem = True
        elif df1[column].dtype != expected_dtype:
            print(f"{RED}Column '{column}' has incorrect type. Expected {expected_dtype} but got {df1[column].dtype}.{RESET}")
            problem = True
        else:
            print(f"{GREEN}Column '{column}' exists and has the correct type ({expected_dtype}).{RESET}")

    for column, expected_dtype in EXPECTED_CATEGORY_COLS.items():
        if column not in df2.columns:
            print(f"{RED}Column '{column}' is missing.{RESET}")
            problem = True
        elif df2[column].dtype != expected_dtype:
            print(f"{RED}Column '{column}' has incorrect type. Expected {expected_dtype} but got {df2[column].dtype}.{RESET}")
            problem = True
        else:
            print(f"{GREEN}Column '{column}' exists and has the correct type ({expected_dtype}).{RESET}")

    if problem:
        return False
    else:
        print("Data Validation Successful")
        return True





