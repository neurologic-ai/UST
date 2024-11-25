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
    'Subcategory2' : 'object'
}


EXCLUDE_SUBCATEGORIES = ['Water']#, 'Coffee/Tea']

STRICT_CATEGORY_RULES = {
            'Food': ['Home Decor', 'Cloths', 'Personal Care', 'Medicine', 'Toys', 'Reading'],
            'Beverage': ['Home Decor', 'Cloths', 'Personal Care', 'Medicine', 'Toys', 'Reading'],
            'Medicine': ['Home Decor', 'Cloths', 'Personal Care', 'Toys'],
            'Toys': ['Medicine']
        }

MONO_CATEGORIES = [
            'Water', 'Juice', 'Coffee/Tea', 'Soda/Soft Drink', 'Smoothie', 'Fries', 
            'Protein Drinks', 'Cold Coffee', 'Cereal', 'Pastry', 'Condiments', 'Dairy', 'Burgers', 'Coke'
        ]

CROSS_CATEGORIES = {
            'Burger': ['Fries', 'Coke'],
            'Sandwich': ['Soda', 'Soft Drink'],
            'Salad': ['Protein (Chicken/Meat)'],
            'Snack': ['Snack', 'Soda/Soft Drink'],
            'Meal': ['Coke', 'Soda'],
            'Wrap': ['Juice'],
            'Smoothie': ['Fruit'],
            'Burrito': ['Side'],
            'Cold Coffee': ['Pastry'],
            'Cereal': ['Milk'],
            'Apparel': ['Bags'],
            'Platter': ['Drink'],
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

MAX_SUBCATEGORY_LIMIT = 3