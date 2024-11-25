from collections import defaultdict
import pandas as pd
from configs.manager import settings
from configs.constant import EXCLUDE_SUBCATEGORIES, STRICT_CATEGORY_RULES, MONO_CATEGORIES, CROSS_CATEGORIES, TIME_SLOTS, MAX_SUBCATEGORY_LIMIT

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
    p_n = str(row['Product_name']).strip().lower()
    cat = str(row['Category']).strip().lower()
    scat1 = str(row['Subcategory']).strip().lower()
    scat2 = str(row['Subcategory2']).strip().lower()
    scat3 = str(row['Subcategory3']).strip().lower()
    categories_dct[p_n] = Product(p_n, cat, scat1, scat2, scat3)

class Aggregation:
    def __init__(self, reco_list, cart_items, categories, current_hour,
                 excluded_subcategories = EXCLUDE_SUBCATEGORIES,
                 strict_category_rules = STRICT_CATEGORY_RULES,
                 mono_subcategories = MONO_CATEGORIES,
                 cross_subcategories = CROSS_CATEGORIES,
                 time_slots = TIME_SLOTS,
                 max_subcategory_limit = MAX_SUBCATEGORY_LIMIT):
        
        self.reco_list = reco_list
        self.cart_items = cart_items
        self.categories = categories
        self.current_hour = current_hour
        
        self.excluded_subcategories = excluded_subcategories
        self.strict_category_rules = strict_category_rules
        self.mono_subcategories = mono_subcategories
        self.cross_subcategories = cross_subcategories
        self.time_slots = time_slots
        self.max_subcategory_limit = max_subcategory_limit

    def exclude_cart_items(self):
        """Remove items already in the cart from the recommendation list."""
        self.reco_list = [p for p in self.reco_list if p not in self.cart_items]
        
    def exclude_obvious_categories(self):
        """Remove products from excluded subcategories."""
        self.reco_list = [
            p for p in self.reco_list 
            if self.categories[p.strip()].subcategory1 not in self.excluded_subcategories
        ]

    def remove_non_timely_products(self):
        """Exclude products that are not appropriate for the current time."""
        self.reco_list = [
            p for p in self.reco_list
            if self.categories[p.strip()].subcategory3 not in self.time_slots
            or self.current_hour in range(*self.time_slots[self.categories[p.strip()].subcategory3])
        ]
    
    def prioritize_associations(self):
        """Prioritize and filter products based on cart items."""
        if not self.cart_items:
            return

        cart_subcats = {self.categories[p.strip()].subcategory1 for p in self.cart_items if self.categories[p.strip()].subcategory1 in self.mono_subcategories}

        # Remove items in the same mono subcategory
        self.reco_list = [
            p for p in self.reco_list 
            if self.categories[p.strip()].subcategory1 not in cart_subcats
        ]

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

        # Prioritize cross-subcategory recommendations
        last_cart_item = self.cart_items[-1]
        cart_subcat1 = self.categories[last_cart_item.strip()].subcategory1
        if cart_subcat1 in self.cross_subcategories:
            prioritized_items = [p for p in self.reco_list 
                                 if self.categories[p.strip()].subcategory1 in self.cross_subcategories[cart_subcat1]]
            
            # print('Product name', 'Subcategory')
            # for prod in self.reco_list:
            #     print(f"{prod}: {self.categories[prod.strip()].subcategory1}")

            # print(f"Recommendation list: {self.reco_list}")
            # print(f"Priorotize list: {prioritized_items}")
            # print('Product name', 'Subcategory')
            # for prod in prioritized_items:
            #     print(f"{prod}: {self.categories[prod.strip()].subcategory1}")

            self.reco_list = prioritized_items + [item for item in self.reco_list if item not in prioritized_items]

    def limit_same_category_occurrences(self):
        """Limit the number of products from the same category."""
        category_count = defaultdict(int)
        refined_list = []

        for p in self.reco_list:
            subcategory = self.categories[p.strip()].subcategory1
            if category_count[subcategory] < self.max_subcategory_limit:
                category_count[subcategory] += 1
                refined_list.append(p)

        self.reco_list = refined_list
    
    def exclude_shorter_product_names(self):
        self.reco_list = [item for item in self.reco_list if len(item) > 1]

    def get_final_recommendations(self):
        """Execute all filtering and return the final list of recommended products."""
        self.exclude_cart_items()
        self.exclude_obvious_categories()
        self.remove_non_timely_products()
        self.prioritize_associations()
        self.limit_same_category_occurrences()
        self.exclude_shorter_product_names()
        return self.reco_list