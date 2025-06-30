SESSION_COL = 'Session_id'
DATE_COL = 'Datetime'
PRODUCT_NAME_COL = 'Product_name'
QUANTITY_COL = 'Quantity'
TIMINGS_COL = 'Timing'
UPC_COL = 'UPC'


TIME_SLOTS = {
            'Breakfast': (5, 12),
            'Breakfast/Lunch': (5, 16),
            'Lunch': (12, 16),
            'Lunch/Dinner': (12, 24),
            'Dinner': (16, 24),
            'Other': (24, 5)
        }

TIMINGS = ['Breakfast', 'Lunch', 'Dinner', 'Other']