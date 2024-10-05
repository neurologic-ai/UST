from fastapi import APIRouter
from bson.json_util import dumps
import json
from db import database
from collections import defaultdict
from models.inputdata import InputData, to_serializable
from models.hepler import categories_dct, Aggregation
from db.database import popular_collection_name, time_collection_name, weather_collection_name, calendar_collection_name, association_collection_name

router = APIRouter()

@router.get("/")
async def get_data():
    data = {}
    data = popular_collection_name.find()
    return dumps(data)
##Middleware CORS layer, 
## to use HTTPS SSL(CERT BOT) Certificate generate has to be routed through NGNIX, Authentication implementation JWT, Timezone, Shop location

@router.post("/")
async def recommendation(data: InputData):
    # Required inputs
    ######################################
    top_n = 50
    cart_items = data.cart_items
    current_hr = 20
    current_dayofweek = 5
    current_weather_category = 'Moderate'
    current_holiday = ''

    ######################################
    # Initialize a dictionary to track the count of product appearances across all sources
    product_count = defaultdict(int)

    # Time Recommendation
    time_recommendation = time_collection_name.find_one({'hr': current_hr, 'dayofweek': current_dayofweek})
    time_recommendations = time_recommendation.get("recommended_products", [])[:top_n] if time_recommendation else []
    for product in time_recommendations:
        product_count[product] += 1  # Increment count for each product

    # Weather Recommendation
    weather_recommendation = weather_collection_name.find_one({'category': current_weather_category})
    weather_recommendations = weather_recommendation.get("products", [])[:top_n] if weather_recommendation else []
    for product in weather_recommendations:
        product_count[product] += 1  # Increment count for each product

    # Calendar Recommendation
    calendar_recommendation = calendar_collection_name.find_one({'holiday': current_holiday})
    calendar_recommendations = calendar_recommendation.get("products", [])[:top_n] if calendar_recommendation else []
    for product in calendar_recommendations:
        product_count[product] += 1  # Increment count for each product

    # Association Products based on all cart items
    assoc_products = {}
    if cart_items:
        for product in cart_items:
            assoc_recommendation = association_collection_name.find_one({"product": product})
            if assoc_recommendation:
                assoc_products = assoc_recommendation.get("associate_products", {})
                # Add or update product counts in product_count
                for assoc_product in list(assoc_products.keys())[:top_n]:
                    product_count[assoc_product] += 1  # Increment count for each product

    # Popular Recommendation
    popular_recommendation = popular_collection_name.find_one()
    popular_recommendations = list(popular_recommendation.get("popular_data", {}).keys())[:top_n] if popular_recommendation else []
    for product in popular_recommendations:
        product_count[product] += 1  # Increment count for each product


    # Sort products by their appearance count across all sources
    sorted_products = sorted(product_count.items(), key = lambda x: x[1], reverse=True)

    # Extract only the product names (not the counts) and take the top_n
    all_recommendations = [product for product, count in sorted_products][:top_n]

    # Return final recommendations
    aggregator = Aggregation(all_recommendations, cart_items, categories_dct, current_hr)
    final_recommendations = aggregator.get_final_recommendations()
    return  final_recommendations
    # return popular_recommendations, time_recommendations, weather_recommendations, calendar_recommendations, assoc_products, product_count