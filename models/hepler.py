from collections import defaultdict
from dataclasses import dataclass
from loguru import logger
from configs.constant import EXCLUDE_SUBCATEGORIES, STRICT_CATEGORY_RULES, MONO_CATEGORIES, CROSS_CATEGORIES, TIME_SLOTS, MAX_SUBCATEGORY_LIMIT, CATEGORY_DATA_PATH, WEATHER_FILTERS

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

class Aggregation:
    def __init__(self, reco_list, cart_items, categories, current_hour, weather,
                 excluded_subcategories=EXCLUDE_SUBCATEGORIES,
                 strict_category_rules=STRICT_CATEGORY_RULES,
                 mono_subcategories=MONO_CATEGORIES,
                 cross_subcategories=CROSS_CATEGORIES,
                 time_slots=TIME_SLOTS,
                 max_subcategory_limit=MAX_SUBCATEGORY_LIMIT):
        
        self.reco_list = reco_list
        self.cart_items = cart_items
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
        self.reco_list = [p for p in self.reco_list if p not in self.cart_items]

    def exclude_obvious_categories(self):
        self.reco_list = [
            p for p in self.reco_list
            if self.categories.get(p.strip()) and self.categories[p.strip()].subcategory not in self.excluded_subcategories
        ]

    def remove_non_timely_products(self):
        self.reco_list = [
            p for p in self.reco_list
            if self.categories.get(p.strip()) and (
                self.categories[p.strip()].timing not in self.time_slots
                or self.current_hour in range(*self.time_slots[self.categories[p.strip()].timing])
            )
        ]

    def prioritize_associations(self):
        if not self.cart_items:
            return

        cart_subcats = {
            self.categories[p.strip()].subcategory
            for p in self.cart_items
            if self.categories.get(p.strip())
        }

        self.reco_list = [
            p for p in self.reco_list
            if self.categories.get(p.strip()) and self.categories[p.strip()].subcategory not in cart_subcats
        ]

        cart_cats = {
            self.categories[p.strip()].category
            for p in self.cart_items
            if self.categories.get(p.strip())
        }

        conflicting_categories = set()
        for cart_cat in cart_cats:
            if cart_cat in self.strict_category_rules:
                conflicting_categories.update(self.strict_category_rules[cart_cat])

        self.reco_list = [
            p for p in self.reco_list
            if self.categories.get(p.strip()) and self.categories[p.strip()].category not in conflicting_categories
        ]

        last_cart_item = self.cart_items[-1].strip()
        if self.categories.get(last_cart_item):
            cart_subcat1 = self.categories[last_cart_item].subcategory
            if cart_subcat1 in self.cross_subcategories:
                prioritized_items = [
                    p for p in self.reco_list
                    if self.categories.get(p.strip()) and self.categories[p.strip()].subcategory in self.cross_subcategories[cart_subcat1]
                ]
                self.reco_list = prioritized_items + [item for item in self.reco_list if item not in prioritized_items]

    def limit_same_category_occurrences(self):
        category_count = defaultdict(int)
        refined_list = []

        for p in self.reco_list:
            category = self.categories.get(p.strip())
            if category:
                subcategory = category.subcategory
                if category_count[subcategory] < self.max_subcategory_limit:
                    category_count[subcategory] += 1
                    refined_list.append(p)

        self.reco_list = refined_list

    def exclude_shorter_product_names(self):
        self.reco_list = [item for item in self.reco_list if len(item) > 1]

    def filter_by_weather(self):
        filters = WEATHER_FILTERS.get(self.weather, {})
        avoid_subcats = set(filters.get("avoid", []))
        prefer_subcats = set(filters.get("prefer", []))

        self.reco_list = [
            p for p in self.reco_list
            if self.categories.get(p.strip()) and self.categories[p.strip()].subcategory not in avoid_subcats
        ]

        preferred = [
            p for p in self.reco_list
            if self.categories.get(p.strip()) and self.categories[p.strip()].subcategory in prefer_subcats
        ]
        others = [
            p for p in self.reco_list
            if self.categories.get(p.strip()) and self.categories[p.strip()].subcategory not in prefer_subcats
        ]

        self.reco_list = preferred + others

    def get_final_recommendations(self):
        self.exclude_cart_items()
        self.exclude_obvious_categories()
        # self.remove_non_timely_products()
        self.prioritize_associations()
        self.limit_same_category_occurrences()
        self.exclude_shorter_product_names()
        self.filter_by_weather()
        return self.reco_list