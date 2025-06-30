from concurrent.futures import ThreadPoolExecutor, as_completed
from vertexai.preview.generative_models import GenerativeModel
from google.oauth2 import service_account
import vertexai
import yaml
from manager import settings
from enum import Enum
import re
import traceback
from typing import List, Dict, Optional
from pydantic import BaseModel, Field, validator, ValidationError
import json
from loguru import logger
import time
from cat_subcat_map import category_dict

# === Enumerations ===
class Category(str, Enum):
    snack = "Snack"
    beverage = "Beverage"
    food = "Food"
    accessories = "Accessories"
    medicine = "Medicine"
    home_decor = "Home Decor"
    miscellaneous = "Miscellaneous"
    personal_care = "Personal Care"
    clothes = "Clothes"
    dessert = "Dessert"
    toys = "Toys"
    unknown = "Unknown"
    book = "Book"
    read = "Read"

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
    Alltime = 'All time'

VALID_TIMINGS = {"Breakfast", "Lunch", "Dinner", "All time"}

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
    category: str
    subcategory: Optional[str]
    timing: Timing



def clean_llm_response(text: str) -> str:
    # Step 1: Remove markdown fences
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.DOTALL).strip()

    # Step 2: Try parsing first
    try:
        json.loads(cleaned)
        return cleaned  # Already valid
    except json.JSONDecodeError:
        # Step 3: Escape problematic backslashes
        cleaned = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', cleaned)
        return cleaned



class ClassificationService:
    def __init__(self, project: str, location: str, service_account_path: str, batch_size: int = 150):
        credentials = service_account.Credentials.from_service_account_file(
            service_account_path, scopes=[settings.GEMINI_API_SCOPE]
        )
        vertexai.init(project=project, location=location, credentials=credentials)
        self.model = GenerativeModel(settings.GEMINI_MODEL)
        self.batch_size = batch_size

    def _build_prompt(self, products: List[str]) -> str:
        allowed_categories = list(category_dict.keys())
        allowed_timings = list(VALID_TIMINGS)

        # Build category + subcategory constraints section
        category_constraints = "Valid categories and their subcategories are:\n"
        for category, subcategories in category_dict.items():
            category_constraints += f"- {category}: {', '.join(subcategories)}\n"

        prompt_dict = {
            "task": "classify_products",
            "description": (
                "You are a strict classifier. For each product name, classify it into:\n"
                "- category: one of the allowed categories below\n"
                "- subcategory: must belong to the selected category's allowed subcategories\n"
                "- timing: exactly one of " + str(allowed_timings) + " (not a list).\n\n"
                f"{category_constraints}\n"
                "Rules:\n"
                "1. DO NOT use multiple values or lists for timing.\n"
                "2. If the product is water or a variant (e.g., 'mineral water', 'Smart Water', 'kinley', 'Aquafina', 'Bisleri'),\n"
                "   then:\n"
                "   - category should be 'Beverage'\n"
                "   - subcategory should be 'Water'\n"
                "   - timing should be 'All time'."
            ),
            "input": products,
            "output_format": (
                "At the end of the process the required response is ONLY this JSON structure:\n"
                '[\n'
                '  {"product": Lays, "category": Snack, "subcategory": Chips, "timing": All time},\n'
                '  {"product": Kinley, "category": Beverage, "subcategory": Water, "timing": All time}\n'
                ']'
            )
        }

        yaml_prompt = yaml.dump(prompt_dict, sort_keys=False)
        
        # logger.debug("==== Generated YAML Prompt ====")
        # logger.debug(yaml_prompt)
        # logger.debug("================================")

        return yaml_prompt


    def _classify_batch(self, products: list[str]) -> List[ProductOutput]:
        logger.debug(f"{len(products)} new products to classify.")
        prompt = self._build_prompt(products)
        logger.debug(f"Length of prompt: {len(prompt)} characters")
        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            logger
            if not text:
                logger.error("Empty response from Gemini")
                raise ValueError("Empty response")

            # logger.debug(f"Raw LLM response: {text}")

            try:
                cleaned = clean_llm_response(text)
                data = json.loads(cleaned)
            except json.JSONDecodeError:
                logger.warning("Malformed JSON from Gemini response.")
                # logger.debug(text)
                logger.debug(traceback.format_exc())
                # raise

            cleaned_data = []
            for item in data:
                if item.get("timing") not in VALID_TIMINGS:
                    logger.warning(f"Invalid timing '{item.get('timing')}', defaulting to 'All time'")
                    item["timing"] = "All time"
                cleaned_data.append(ProductOutput(**item))

            return cleaned_data
        except Exception as e:
            logger.debug(f"ERROR:root:Gemini classification error: {e}")
            return [ProductOutput(product=p, category=Category.snack,subcategory=Subcategory.unknown, timing=Timing.Alltime) for p in products]
    
    
    def classify(self, products: List[str]) -> List[ProductOutput]:
        inputs = [p.strip() for p in products if p and p.strip()]
        results = []
        to_classify = inputs

        logger.info(f"{len(to_classify)} new products to classify.")
        batch_size = self.batch_size
        max_workers = 4  # or make it a class argument

        batches = [
            to_classify[i:i + batch_size]
            for i in range(0, len(to_classify), batch_size)
        ]

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_batch = {
                executor.submit(self._classify_batch, batch): batch
                for batch in batches
            }

            for future in as_completed(future_to_batch):
                batch_result = future.result()
                results.extend(batch_result)

        return results