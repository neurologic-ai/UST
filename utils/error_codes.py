# error_codes.py

UPLOAD_ERRORS = {
    "INVALID_FILE_TYPE": {"errorCode": "RE-XLS-001", "message": "File must be .csv or .xlsx"},
    "MISSING_COLUMNS": {"errorCode": "RE-XLS-002", "message": "Required columns are missing."},
    "EMPTY_VALUES": {"errorCode": "RE-XLS-003", "message": "Empty UPC or Product Name values found."},
    "ALL_UPCS_INVALID": {"errorCode": "RE-XLS-004", "message": "All uploaded UPCs are invalid."},
}


UPLOAD_SUCCESS = {
    "PARTIAL": "RE-XLS-005",
    "ALL_VALID": ""
}
