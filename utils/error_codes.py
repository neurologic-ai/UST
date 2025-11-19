# error_codes.py

UPLOAD_ERRORS = {
    "INVALID_FILE_TYPE": {"errorCode": "RE-XLS-001", "message": "File must be .csv or .xlsx"},
    "SCIENTIFIC_NOTATION_UPC": {"errorCode": "RE-XLS-007", "message": "UPC values contain scientific notation, which corrupts identifiers."},
    "MISSING_COLUMNS": {"errorCode": "RE-XLS-002", "message": "Required columns are missing."},
    "EMPTY_VALUES": {"errorCode": "RE-XLS-003", "message": "Empty UPC or Product Name values found."},
    "ALL_UPCS_INVALID": {"errorCode": "RE-XLS-004", "message": "All uploaded UPCs are invalid."},
    "DUPLICATE_DATA": {"errorCode": "RE-XLS-006", "message": "Data quality issues found in the file."},
}


UPLOAD_SUCCESS = {
    "PARTIAL": "RE-XLS-005",
    "ALL_VALID": ""}