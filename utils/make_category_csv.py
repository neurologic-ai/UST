from enum import Enum
from typing import List, Dict, Tuple, Optional
from pydantic import BaseModel, Field, validator, ValidationError
import openai
import json
from loguru import logger
# === Enumerations for strong typing ===
class Category(str, Enum):
    beverage = 'beverage'
    snack = 'snack'
    playing_item = 'playing item'
    meal = 'meal'
    # Extend with more categories as needed
class Subcategory(str, Enum):
    candy = 'Candy'
    unknown = 'Unknown'
    chips = 'Chips'
    coffee = 'Coffee'
    sandwich = 'Sandwich'
    clothing = 'Clothing'
    energy_drink = 'Energy Drink'
    cookies = 'Cookies'
    juice = 'Juice'
    chocolate = 'Chocolate'
    sticker = 'Sticker'
    pastry = 'Pastry'
    jerky = 'Jerky'
    crackers = 'Crackers'
    nuts = 'Nuts'
    water = 'Water'
    miscellaneous = 'Miscellaneous'
    soda = 'Soda'
    dessert = 'Dessert'
    sports_drink = 'Sports Drink'
    hot_drink = 'Coffee/Tea'
    toys = 'Toys'
    ice_cream = 'Ice Cream'
    pasta = 'Pasta'

class Timing(str, Enum):
    Breakfast = 'Breakfast'
    Lunch = 'Lunch'
    Dinner = 'Dinner'
    Alltime = 'Alltime'
# === Pydantic models for inputs/outputs ===
class ProductInput(BaseModel):
    name: str = Field(..., description="Product name (non-empty)")
    @validator('name')
    def name_must_not_be_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('Product name must not be empty')
        return v
class ProductOutput(BaseModel):
    product: str
    category: Category
    subcategory: Optional[str]
    timing: Timing


# === Classification service ===
class ClassificationService:
    # Predefined mapping of known products
    _class_map: Dict[str, Tuple[Category, Subcategory, Timing]] = {
        'coke':      (Category.beverage, Subcategory.soda, Timing.Alltime),
        'pepsi':     (Category.beverage, Subcategory.soda, Timing.Alltime),
        'tea':       (Category.beverage, Subcategory.hot_drink, Timing.Breakfast),
        'coffee':    (Category.beverage, Subcategory.hot_drink, Timing.Breakfast),
        'sandwich':  (Category.snack, Subcategory.sandwich, Timing.Breakfast),
        'burger':    (Category.snack, Subcategory.unknown, Timing.Lunch),
        'chips':     (Category.snack, Subcategory.chips, Timing.Alltime),
        'chocolate': (Category.snack, Subcategory.chocolate, Timing.Alltime),
        'pizza':     (Category.snack, Subcategory.unknown, Timing.Dinner),
        'carrom':    (Category.playing_item, Subcategory.toys, Timing.Alltime),
        'ludo':      (Category.playing_item, Subcategory.toys, Timing.Alltime),
        'water':     (Category.beverage, Subcategory.water, Timing.Alltime),
        'biryani':   (Category.meal, Subcategory.unknown, Timing.Lunch),
        'pasta':     (Category.meal, Subcategory.pasta, Timing.Dinner),
        'bread':     (Category.snack, Subcategory.unknown, Timing.Breakfast),
        'juice':     (Category.beverage, Subcategory.juice, Timing.Breakfast),
        'ice cream': (Category.snack, Subcategory.ice_cream, Timing.Alltime),
    }
    def __init__(self, api_key: str, model: str = 'gpt-4o'):
        openai.api_key = api_key
        self.model = model
        # Simple in-memory cache for unknown products
        self._cache: Dict[str, ProductOutput] = {}
    def _build_prompt(self, products: List[str]) -> str:
        items = ', '.join(products)
        # return (
        #     f"Classify the following products into category (beverage, snack, playing item, meal, etc.) "
        #     f"and consumption timing (Breakfast, Lunch, Dinner, Alltime):\n\nProducts: [{items}]\n\n"
        #     f"Respond ONLY in JSON array format: "
        #     f"[{ '{' }"product": "name", "category": "...", "timing": "..."{ '}' }, ...]"
        #     )
        return (
            f"Classify the following products into:\n"
            f"- category (e.g., beverage, snack, playing item, meal)\n"
            f"- subcategory (e.g., soda, chips, board game, rice dish)\n"
            f"- timing (Breakfast, Lunch, Dinner, Alltime)\n\n"
            f"Products: [{items}]\n\n"
            f"Respond ONLY in JSON array format:\n"
            f'[{{"product": "name", "category": "...", "subcategory": "...", "timing": "..."}}]'
        )
    def _classify_with_llm(self, products: List[str]) -> List[ProductOutput]:
        prompt = self._build_prompt(products)
        try:
            resp = openai.ChatCompletion.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            text = resp.choices[0].message.content
            raw = json.loads(text)
            results: List[ProductOutput] = []
            for entry in raw:
                try:
                    out = ProductOutput(**entry)
                    results.append(out)
                    # populate cache
                    self._cache[out.product.lower()] = out
                except ValidationError as e:
                    # Skip invalid entries or log
                    continue
            return results
        except Exception as e:
            # On error, return unknowns with default values
            return [
                ProductOutput(product=p, category=Category.snack, subcategory=Subcategory.unknown, timing=Timing.Alltime)
                for p in products
            ]
            # return [ProductOutput(product=p, category=Category.snack, timing=Timing.Alltime) for p in products]
    def classify(self, products: List[str]) -> List[ProductOutput]:
        inputs = [ProductInput(name=p).name for p in products]
        known_results: List[ProductOutput] = []
        to_classify: List[str] = []
        # Partition into known, cached, and unknown
        for name in inputs:
            key = name.lower()
            if key in self._class_map:
                cat, subcat, tim = self._class_map[key]
                known_results.append(ProductOutput(product=name, category=cat, subcategory=subcat, timing=tim))
            elif key in self._cache:
                known_results.append(self._cache[key])
            else:
                to_classify.append(name)
        logger.debug(to_classify)
        # Query LLM for the rest
        llm_results = self._classify_with_llm(to_classify) if to_classify else []
        logger.debug(llm_results)
        return known_results + llm_results
