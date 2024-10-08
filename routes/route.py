import asyncio
from fastapi import APIRouter, Depends, logger
from fastapi.encoders import jsonable_encoder
from bson.json_util import dumps
from collections import defaultdict

from fastapi.responses import JSONResponse
from odmantic import AIOEngine
from models.schema import RecommendationRequestBody
from models.hepler import categories_dct, Aggregation
from db.singleton import get_engine
from models.db import Association_collection
from utils.helper import get_association_recommendations, get_calendar_recommendation, get_popular_recommendation, get_time_recommendation, get_weather_recommendation

router = APIRouter()

@router.get("/")
async def get_data(
    db: AIOEngine = Depends(get_engine)
):
   
    data= await db.find(Association_collection)
    return data


@router.post("/")
async def recommendation(
    data: RecommendationRequestBody,
    db: AIOEngine = Depends(get_engine)
):
    # Required inputs
    ######################################
    top_n = data.top_n
    cart_items = data.cart_items
    current_hr = data.current_hr
    current_dayofweek = data.current_dayofweek
    current_weather_category = data.current_weather_category
    current_holiday = data.current_holiday

    ######################################
    # Initialize a dictionary to track the count of product appearances across all sources
    product_count = defaultdict(int)

    # Gather all recommendations concurrently
    time_recommendations, weather_recommendations, calendar_recommendations, assoc_recommendations, popular_recommendations = await asyncio.gather(
        get_time_recommendation(db, current_hr, current_dayofweek, top_n),
        get_weather_recommendation(db, current_weather_category, top_n),
        get_calendar_recommendation(db, current_holiday, top_n),
        get_association_recommendations(db, cart_items, top_n),
        get_popular_recommendation(db, top_n)
    )

    # Aggregate product counts from recommendations
    for product in time_recommendations:
        product_count[product] += 1
    for product in weather_recommendations:
        product_count[product] += 1
    for product in calendar_recommendations:
        product_count[product] += 1
    for product in assoc_recommendations:
        product_count[product] += 1
    for product in popular_recommendations:
        product_count[product] += 1

    # Sort products by their appearance count across all sources
    sorted_products = sorted(product_count.items(), key=lambda x: x[1], reverse=True)

    # Extract only the product names (not the counts) and take the top_n
    all_recommendations = [product for product, count in sorted_products][:top_n]

    # Return final recommendations
    aggregator = Aggregation(all_recommendations, cart_items, categories_dct, current_hr)
    final_recommendations = aggregator.get_final_recommendations()
    return final_recommendations


# ------------------------------- OLDER CODE ------------------------------- #


# @router.post("/")
# async def recommendation(
#     data: RecommendationRequestBody):
#     # Required inputs
#     ######################################
#     top_n = data.top_n
#     cart_items = data.cart_items
#     current_hr = data.current_hr
#     current_dayofweek = data.current_dayofweek
#     current_weather_category = data.current_weather_category
#     current_holiday = data.current_holiday

#     ######################################
#     # Initialize a dictionary to track the count of product appearances across all sources
#     product_count = defaultdict(int)

#     # Time Recommendation
#     time_recommendation = time_collection_name.find_one({'hr': current_hr, 'dayofweek': current_dayofweek})
#     time_recommendations = time_recommendation.get("recommended_products", [])[:top_n] if time_recommendation else []
#     for product in time_recommendations:
#         product_count[product] += 1  # Increment count for each product

#     # Weather Recommendation
#     weather_recommendation = weather_collection_name.find_one({'category': current_weather_category})
#     weather_recommendations = weather_recommendation.get("products", [])[:top_n] if weather_recommendation else []
#     for product in weather_recommendations:
#         product_count[product] += 1  # Increment count for each product

#     # Calendar Recommendation
#     calendar_recommendation = calendar_collection_name.find_one({'holiday': current_holiday})
#     calendar_recommendations = calendar_recommendation.get("products", [])[:top_n] if calendar_recommendation else []
#     for product in calendar_recommendations:
#         product_count[product] += 1  # Increment count for each product

#     # Association Products based on all cart items
#     assoc_products = {}
#     if cart_items:
#         for product in cart_items:
#             assoc_recommendation = association_collection_name.find_one({"product": product})
#             if assoc_recommendation:
#                 assoc_products = assoc_recommendation.get("associate_products", {})
#                 # Add or update product counts in product_count
#                 for assoc_product in list(assoc_products.keys())[:top_n]:
#                     product_count[assoc_product] += 1  # Increment count for each product

#     # Popular Recommendation
#     popular_recommendation = popular_collection_name.find_one()
#     popular_recommendations = list(popular_recommendation.get("popular_data", {}).keys())[:top_n] if popular_recommendation else []
#     for product in popular_recommendations:
#         product_count[product] += 1  # Increment count for each product


#     # Sort products by their appearance count across all sources
#     sorted_products = sorted(product_count.items(), key = lambda x: x[1], reverse=True)

#     # Extract only the product names (not the counts) and take the top_n
#     all_recommendations = [product for product, count in sorted_products][:top_n]

#     # Return final recommendations
#     aggregator = Aggregation(all_recommendations, cart_items, categories_dct, current_hr)
#     final_recommendations = aggregator.get_final_recommendations()
#     return  final_recommendations
    # return popular_recommendations, time_recommendations, weather_recommendations, calendar_recommendations, assoc_products, product_count