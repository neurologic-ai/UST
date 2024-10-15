from collections import defaultdict
import pandas as pd
from configs.manager import settings

# Read Categories
df_categories = pd.read_csv(settings.CATEGORY_DATA_LOCATION)

class Product:
    def __init__(self, name = None, category = None, subcategory1 = None, subcategory2 = None, subcategory3 = None):
        self.name = name
        self.category = category
        self.subcategory1 = subcategory1
        self.subcategory2 = subcategory2
        self.subcategory3 = subcategory3

categories_dct = defaultdict(Product)

for idx, row in df_categories.iterrows():
    p_n = row['Product_name']
    cat = row['Category']
    scat1 = row['Subcategory']
    scat2 = row['Subcategory2']
    scat3 = row['Subcategory3']
    categories_dct[str(p_n).strip()] = Product(str(p_n).strip(), cat, scat1, scat2, scat3)

class Aggregation:
    def __init__(self, reco_list, cart_items, categories, current_hour = 12):
        self.reco_list = reco_list
        self.cart_items = cart_items
        self.categories = categories
        self.current_hour = current_hour
        self.max_subcategory_limit = 3
        
        self.excluded_subcategories = ['Water', 'Coffee/Tea', 'Tea', 'Coffee']
        self.strict_category_rules = {
            'Food': ['Home Decor', 'Cloths', 'Personal Care', 'Medicine', 'Toys', 'Reading'],
            'Beverage': ['Home Decor', 'Cloths', 'Personal Care', 'Medicine', 'Toys', 'Reading'],
            'Medicine': ['Home Decor', 'Cloths', 'Personal Care', 'Toys'],
            'Toys': ['Medicine']
        }
        self.mono_subcategories = [
            'Water', 'Juice', 'Coffee/Tea', 'Soda/Soft Drink', 'Smoothie', 'Fries', 
            'Protein Drinks', 'Cold Coffee', 'Cereal', 'Pastry', 'Condiments', 'Dairy', 'Burgers', 'Coke'
        ]
        self.cross_subcategories = {
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
        self.time_slots = {
            'Breakfast': [5, 12],
            'Breakfast/Lunch': [5, 18],
            'Lunch': [12, 18],
            'Lunch/Dinner': [12, 23],
            'Dinner': [18, 23]
        }

    def exclude_cart_items(self):
        """Remove items already in the cart from the recommendation list."""
        self.reco_list = [p for p in self.reco_list if p not in self.cart_items]
        # print(self.reco_list)
        
    def exclude_obvious_categories(self):
        """Remove products from excluded subcategories."""
        # print([self.categories.get(p.strip(), Product()).subcategory1 for p in self.reco_list])
        self.reco_list = [
            p for p in self.reco_list 
            if self.categories[p.strip()].subcategory1 not in self.excluded_subcategories
        ]
        # print([self.categories.get(p.strip(), Product()).subcategory1 for p in self.reco_list])
        # print(self.reco_list)

    def remove_non_timely_products(self):
        """Exclude products that are not appropriate for the current time."""
        self.reco_list = [
            p for p in self.reco_list
            if self.categories[p.strip()].subcategory3 not in self.time_slots
            or self.current_hour in range(*self.time_slots[self.categories[p.strip()].subcategory3])
        ]
        # print(self.reco_list)
    
    def prioritize_associations(self):
        """Prioritize and filter products based on cart items."""
        if not self.cart_items:
            return

        cart_subcats = {self.categories[p.strip()].subcategory1 for p in self.cart_items if self.categories[p.strip()].subcategory1 in self.mono_subcategories}
        # print(cart_subcats)

        # Remove items in the same mono subcategory
        self.reco_list = [
            p for p in self.reco_list 
            if self.categories[p.strip()].subcategory1 not in cart_subcats
        ]
        # print(self.reco_list)
        # Remove conflicting items based on strict category rules
        cart_cats = {self.categories[p.strip()].category for p in self.cart_items}
        conflicting_categories = set()
        for cart_cat in cart_cats:
            if cart_cat in self.strict_category_rules:
                conflicting_categories.update(self.strict_category_rules[cart_cat])
    
        self.reco_list = [
            p for p in self.reco_list 
            if self.categories[p.strip()].category not in conflicting_categories
        ]
        # print(self.reco_list)

        # Prioritize cross-subcategory recommendations
        last_cart_item = self.cart_items[-1]
        cart_subcat1 = self.categories[last_cart_item.strip()].subcategory1
        if cart_subcat1 in self.cross_subcategories:
            prioritized_items = [p for p in self.reco_list 
                                 if self.categories[p.strip()].subcategory1 in self.cross_subcategories[cart_subcat1]]
            self.reco_list = prioritized_items + [item for item in self.reco_list if item not in prioritized_items]
        # print(self.reco_list)

    def limit_same_category_occurrences(self):
        """Limit the number of products from the same category."""
        category_count = defaultdict(int)
        refined_list = []

        for p in self.reco_list:
            subcategory = self.categories[p.strip()].subcategory1
            print(p, subcategory)
            if category_count[subcategory] < self.max_subcategory_limit:
                category_count[subcategory] += 1
                refined_list.append(p)

        self.reco_list = refined_list

    def get_final_recommendations(self):
        """Execute all filtering and return the final list of recommended products."""
        self.exclude_cart_items()
        self.exclude_obvious_categories()
        self.remove_non_timely_products()
        self.prioritize_associations()
        self.limit_same_category_occurrences()
        return self.reco_list


# Example usage
# reco_list = [
#     "Dasani Purified Water 16.9 FL OZ (1.06 PT) 500 mL", "Dasani - 20 oz", "12 oz. Coffee/Tea", 
#     "Quesadillas - Chicken", "Lays Classic Potato Chip", "Twizzlers", "Coke (16.9 fl. Oz)", 
#     "Diet Coke 16.9oz.", "Coke", "Sprite", "Diet Coke", "Egg Salad Bagel", "Hat", 
#     "Cherry Chapstick Blister Card"
# ]

# cart_items = []

# current_hour = 10

# aggregator = Aggregation(reco_list, cart_items, categories_dct, current_hour)
# final_recommendations = aggregator.get_final_recommendations()
# print(final_recommendations)