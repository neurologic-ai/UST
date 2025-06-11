from collections import defaultdict
from dataclasses import asdict, dataclass
from loguru import logger
import pandas as pd
from configs.constant import EXCLUDE_SUBCATEGORIES, STRICT_CATEGORY_RULES, MONO_CATEGORIES, CROSS_CATEGORIES, TIME_SLOTS, MAX_SUBCATEGORY_LIMIT, CATEGORY_DATA_PATH, WEATHER_FILTERS
from utils.file_download import download_file_from_s3
from utils.make_category_csv import normalize_key

# # Use S3 download and read as DataFrame
# url = ""
# file_buffer = download_file_from_s3(url)
# if file_buffer is None:
#     raise Exception("Failed to load CATEGORY_DATA_PATH from S3.")
# df_categories = pd.read_csv(file_buffer)
# Read Categories
# df_categories = pd.read_csv(CATEGORY_DATA_PATH)

@dataclass
class Product:
    def __init__(self, name = None, category = None, subcategory = None, timing = None):
        self.name = name
        self.category = category
        self.subcategory = subcategory
        self.timing = timing
    def to_dict(self):
        return {
            "name": self.name,
            "category": self.category,
            "subcategory": self.subcategory,
            "timing": self.timing
        }


    @staticmethod
    def from_dict(data):
        return Product(
            name=data.get("name"),
            category=data.get("category"),
            subcategory=data.get("subcategory"),
            timing=data.get("timing")
        )
# categories_dct = defaultdict(Product)

# for idx, row in df_categories.iterrows():
#     p_n = str(row['Product_name']).strip().lower()
#     cat = str(row['Category']).strip().lower()
#     scat = str(row['Subcategory']).strip().lower()
#     tim = str(row['Timing']).strip().lower()

#     categories_dct[p_n] = Product(p_n, cat, scat, tim)

class Aggregation:
    def __init__(self, reco_list, cart_items, categories, current_hour, weather,
                 excluded_subcategories = EXCLUDE_SUBCATEGORIES,
                 strict_category_rules = STRICT_CATEGORY_RULES,
                 mono_subcategories = MONO_CATEGORIES,
                 cross_subcategories = CROSS_CATEGORIES,
                 time_slots = TIME_SLOTS,
                 max_subcategory_limit = MAX_SUBCATEGORY_LIMIT):
        
        # self.reco_list = reco_list
        # self.cart_items = cart_items
        self.reco_list = [normalize_key(p) for p in reco_list]
        self.cart_items = [normalize_key(p) for p in cart_items]

        self.categories = categories
        self.current_hour = current_hour
        self.weather = weather.lower()
        
        self.excluded_subcategories = excluded_subcategories
        self.strict_category_rules = strict_category_rules
        self.mono_subcategories = mono_subcategories
        self.cross_subcategories = cross_subcategories
        self.time_slots = time_slots
        self.max_subcategory_limit = max_subcategory_limit

    def exclude_cart_items(self):
        """Remove items already in the cart from the recommendation list."""
        self.reco_list = [p for p in self.reco_list if p not in self.cart_items]
        logger.debug(self.reco_list)
        
    def exclude_obvious_categories(self):
        """Remove products from excluded subcategories."""
        self.reco_list = [
            p for p in self.reco_list 
            if self.categories[p.strip()].subcategory not in self.excluded_subcategories
        ]
        logger.debug(self.reco_list)
    

    def remove_non_timely_products(self):
        """Exclude products that are not appropriate for the current time."""
        self.reco_list = [
            p for p in self.reco_list
            if self.categories[p.strip()].timing not in self.time_slots
            or self.current_hour in range(*self.time_slots[self.categories[p.strip()].timing])
        ]
        logger.debug(self.reco_list)
    def prioritize_associations(self):
        """Prioritize and filter products based on cart items."""
        if not self.cart_items:
            return

        cart_subcats = {self.categories[p.strip()].subcategory for p in self.cart_items if self.categories[p.strip()].subcategory in self.mono_subcategories}

        # Remove items in the same mono subcategory
        self.reco_list = [
            p for p in self.reco_list 
            if self.categories[p.strip()].subcategory not in cart_subcats
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
        cart_subcat1 = self.categories[last_cart_item.strip()].subcategory
        if cart_subcat1 in self.cross_subcategories:
            prioritized_items = [p for p in self.reco_list 
                                 if self.categories[p.strip()].subcategory in self.cross_subcategories[cart_subcat1]]

            # for prod in prioritized_items:
            #     print(f"{prod}: {self.categories[prod.strip()].subcategory}")

            self.reco_list = prioritized_items + [item for item in self.reco_list if item not in prioritized_items]
        logger.debug(self.reco_list)

    def limit_same_category_occurrences(self):
        """Limit the number of products from the same category."""
        category_count = defaultdict(int)
        refined_list = []

        for p in self.reco_list:
            subcategory = self.categories[p.strip()].subcategory
            if category_count[subcategory] < self.max_subcategory_limit:
                category_count[subcategory] += 1
                refined_list.append(p)

        self.reco_list = refined_list
        logger.debug(self.reco_list)
    
    def exclude_shorter_product_names(self):
        self.reco_list = [item for item in self.reco_list if len(item) > 1]
        logger.debug(self.reco_list)

    def filter_by_weather(self):
        """Filter recommendations based on weather conditions."""
        filters = WEATHER_FILTERS.get(self.weather, {})
        avoid_subcats = set(filters.get("avoid", []))
        prefer_subcats = set(filters.get("prefer", []))

        # Avoid unwanted subcategories
        self.reco_list = [
            p for p in self.reco_list 
            if self.categories[p.strip()].subcategory not in avoid_subcats
        ]

        # Prioritize preferred ones
        preferred = [
            p for p in self.reco_list 
            if self.categories[p.strip()].subcategory in prefer_subcats
        ]
        others = [
            p for p in self.reco_list 
            if self.categories[p.strip()].subcategory not in prefer_subcats
        ]

        self.reco_list = preferred + others


    def get_final_recommendations(self):
        """Execute all filtering and return the final list of recommended products."""
        self.exclude_cart_items()
        self.exclude_obvious_categories()
        # self.remove_non_timely_products()
        self.prioritize_associations()
        self.limit_same_category_occurrences()
        self.exclude_shorter_product_names()
        self.filter_by_weather() 
        logger.debug(self.reco_list)
        return self.reco_list
        
    

# def enrich_with_upc(items: list[str], name_to_upc_map: dict) -> list[dict]:
#     return [
#         {
#             "name": item,
#             "upc": name_to_upc_map.get(item.lower(), "")
#         }
#         for item in items
#     ]


# def get_product_names_from_upcs(upcs: list[str], upc_to_name_map: dict) -> list[str]:
#     return [upc_to_name_map.get(upc.strip(), "") for upc in upcs if upc.strip() in upc_to_name_map]
