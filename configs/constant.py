PROCESSED_DATA_PATH = "initialize/Data/processed.csv" # During the deployment we can store it to cloud storage
CATEGORY_PATH = "db/Categories.csv"
GREEN = '\033[92m'
RED = '\033[91m'
RESET = '\033[0m'

EXPECTED_PROCESSED_COLS = {
    'Session_id': 'int64',
    'Date_time': 'object',
    'Product_name': 'object',
    'Quantity': 'int64',
}

SHOP_LOCATION = 'Jackson Hole Airport'

SESSION_COL = 'Session_id'
DATE_COL = 'Datetime'
PRODUCT_NAME_COL = 'Product_name'
QUANTITY_COL = 'Quantity'
TIMINGS_COL = 'Timing'

EXPECTED_CATEGORY_COLS = {
    'Product_name': 'object',
    'Category': 'object',
    'Subcategory': 'object',
    'Subcategory2': 'object',
    'Subcategory3' : 'object'
}


EXCLUDE_SUBCATEGORIES = []#'water']

STRICT_CATEGORY_RULES = {
            'food': ['home decor', 'cloths', 'personal Care', 'medicine', 'toys'],
            'beverage': ['home decor', 'cloths', 'personal Care', 'medicine', 'toys'],
            'medicine': ['home Decor', 'cloths', 'personal Care', 'toys'],
            'toys': ['medicine']
        }

MONO_CATEGORIES = [
            'water', 'juice', 'coffee/tea', 'soda', 'soft drink', 'smoothie', 'fries', 
            'protein drinks', 'cold coffee', 'cereal', 'pastry', 'condiments', 'burgers', 'coke', 'milk'
        ]

CROSS_CATEGORIES = {
            'burger': ['french fries', 'fries', 'coke'],
            'sandwich': ['coffee', 'tea', 'juice', 'coffee/tea', 'soda', 'soft drink'],
            'salad': ['protein'],
            'snack': ['snack', 'soda', 'soft drink'],
            'meal': ['coke', 'soda', 'coffee', 'tea', 'juice', 'coffee/tea', 'soft drink'],
            'wrap': ['juice', 'coffee', 'tea', 'coffee/tea'],
            'smoothie': ['fruit', 'water'],
            'burrito': ['coffee', 'juice', 'tea', 'coffee/tea', 'side', 'soft drink'],
            'cold coffee': ['pastry'],
            'cereal': ['milk', 'coffee', 'tea', 'coffee/tea'],
            'apparel': ['bags'],
            'platter': ['soft drink', 'soda'],
            'medicine': ['water', 'juice']
        }

TIME_SLOTS = {
            'Breakfast': (5, 12),
            'Breakfast/Lunch': (5, 16),
            'Lunch': (12, 16),
            'Lunch/Dinner': (12, 24),
            'Dinner': (16, 24),
            'Other': (24, 5)
        }

TIMINGS = ['Breakfast', 'Lunch', 'Dinner', 'Other']

MAX_SUBCATEGORY_LIMIT = 1