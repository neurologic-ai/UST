from enum import Enum
import re
import traceback
from typing import List, Dict, Optional
from fastapi import HTTPException
from pydantic import BaseModel, Field, validator, ValidationError
from openai import OpenAI
import json
from loguru import logger
import redis
import time

# === Enumerations ===
class Category(str, Enum):
    beverage = 'beverage'
    snack = 'snack'
    playing_item = 'playing item'
    meal = 'meal'

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

# === Pydantic models ===
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

# === Classification Service ===
class ClassificationService:
    def __init__(self, api_key: str, redis_client: redis.Redis, model: str = 'gpt-4o', batch_size: int = 500):
        self.client = OpenAI(api_key=api_key)
        self.redis = redis_client
        self.model = model
        self.batch_size = batch_size

    def _build_prompt(self, products: List[str]) -> str:
        items = ', '.join(f'"{p}"' for p in products)
        return (
            "You are a strict JSON-only classifier.\n"
            "Classify each product into:\n"
            "- category: e.g., beverage, snack, playing item, meal\n"
            "- subcategory: more specific type, like soda, chips, board game, rice dish\n"
            "- timing: when people generally consume or use it — choose from [Breakfast, Lunch, Dinner, Alltime].\n"
            "  Use 'Alltime' only if the product is commonly used or eaten at any time of day.\n\n"
            "Input:\n"
            f"[{items}]\n\n"
            "Output:\n"
            "Respond ONLY with a JSON array of this format (no preface, no explanation):\n"
            '[\n'
            '  {"product": "name", "category": "snack", "subcategory": "chips", "timing": "Alltime"},\n'
            '  {"product": "name", "category": "beverage", "subcategory": "tea", "timing": "Breakfast"}\n'
            ']'
        )


    def _classify_batch(self, products: List[str]) -> List[ProductOutput]:
        prompt = self._build_prompt(products)
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a strict JSON-only classifier. Only output a JSON array. No explanation."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=2048
            )
            text = resp.choices[0].message.content.strip()

            if not text:
                logger.error("Empty response from OpenAI")
                raise ValueError("Empty response")

            logger.debug(f"Raw LLM response: {text}")

            # Try parsing directly
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                logger.warning("Malformed JSON detected, attempting to auto-correct...")

                # Fix incomplete JSON by trimming to last full object
                fixed_text = re.sub(r',?\s*\{\s*"product"\s*:\s*".*$', '', text.strip(), flags=re.DOTALL)
                fixed_text = fixed_text.strip().rstrip(',')  # remove trailing comma
                fixed_text = f"[{fixed_text}]" if not fixed_text.startswith("[") else f"{fixed_text}]"

                logger.debug(f"Fixed JSON: {fixed_text}")
                return json.loads(fixed_text)

        except Exception as e:
            logger.exception(f"LLM classification error: {e}")
            raise
            # return [
            #     ProductOutput(
            #         product=p,
            #         category=Category.snack,
            #         subcategory=Subcategory.unknown,
            #         timing=Timing.Alltime
            #     ) for p in products
            # ]


    def classify(self, products: List[str]) -> List[ProductOutput]:
        inputs = [ProductInput(name=p).name for p in products]
        results = []
        to_classify = []

        for name in inputs:
            cached = self.redis.get(name.lower())
            if cached:
                try:
                    obj = ProductOutput(**json.loads(cached))
                    results.append(obj)
                except ValidationError:
                    to_classify.append(name)
            else:
                to_classify.append(name)

        logger.info(f"{len(to_classify)} new products to classify.")

        # Batch classify
        for i in range(0, len(to_classify), self.batch_size):
            batch = to_classify[i:i+self.batch_size]
            # logger.debug(f"Classifying batch: {batch}")
            batch_results = self._classify_batch(batch)
            results.extend(batch_results)
            time.sleep(1)  # Rate-limit to avoid hitting OpenAI too hard

        return results
