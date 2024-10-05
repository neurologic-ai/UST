import holidays

PROCESSED_DATA_PATH = "initial/Data/processed.csv"
GREEN = '\033[92m'
RED = '\033[91m'
RESET = '\033[0m'

EXPECTED_COLS = {
    'Session_id': 'int64',
    'Date_time': 'object',
    'Product_name': 'object',
    'Quantity': 'int64',
}

# Load US holidays for the years of interest
US_HOLIDAYS = holidays.US(years = range(2015, 2035))  # Adjust years based on your data

SHOP_LOCATION = 'Jackson Hole Airport'
DATE_COL = 'Date_time'
