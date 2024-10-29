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
            'Breakfast': [5, 10],
            'Breakfast/Lunch': [5, 18],
            'Lunch': [10, 18],
            'Lunch/Dinner': [10, 23],
            'Dinner': [18, 23]
        }

MAX_SUBCATEGORY_LIMIT = 3

CATEGORY_PATH = "db/Categories.csv"
PROCESSED_PATH = "initial/Data/processed.csv"