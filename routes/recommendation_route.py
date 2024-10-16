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
from routes.user_route import PermissionChecker
from utils.helper import get_association_recommendations, get_calendar_recommendation, get_popular_recommendation, get_time_recommendation, get_weather_recommendation
from configs.constant import PROCESSED_PATH, CATEGORY_PATH
from initial.data_validation import validate
from setup import run_models_and_store_outputs

router = APIRouter()

@router.get("/view data")
async def get_data(
    db: AIOEngine = Depends(get_engine)
):
   
    data= await db.find(Association_collection)
    return data


@router.post("/recommendation")
async def recommendation(
    data: RecommendationRequestBody,
    # athorize:bool=Depends(PermissionChecker(['items:read'])),
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
    for product in assoc_recommendations:
        product_count[product] += 1
    for product in weather_recommendations:
        product_count[product] += 1
    for product in time_recommendations:
        product_count[product] += 1
    for product in calendar_recommendations:
        product_count[product] += 1
    for product in popular_recommendations:
        product_count[product] += 1

    # Sort products by their appearance count across all sources
    sorted_products = sorted(product_count.items(), key = lambda x: x[1], reverse = True)

    # Extract only the product names (not the counts) and take the top_n
    all_recommendations = [product for product, _ in sorted_products][:top_n]

    # Return final recommendations
    aggregator = Aggregation(all_recommendations, cart_items, categories_dct, current_hr)
    final_recommendations = aggregator.get_final_recommendations()
    return final_recommendations

from fastapi import FastAPI, UploadFile, File
import pandas as pd 
# pip install python-multipart

@router.post("/setup")
async def upload_csvs(
    processed: UploadFile = File(...), 
    categories: UploadFile = File(...)
):
    # Read both files into pandas DataFrames
    df1 = pd.read_csv(processed.file)
    df2 = pd.read_csv(categories.file)
    # Lets see is the input files are in correct format
    validation = validate(df1, df2)
    if not validation:
        print(f"Error: Validation failed, please try again with correct data format.")
        return {"Error": "Validation failed, please try again with correct data format."}

    # Store the input files
    df1.to_csv(PROCESSED_PATH, index = False)
    df2.to_csv(CATEGORY_PATH, index = False)
    print("Data is stored successfully")
    try:
        run_models_and_store_outputs()
    except:
        return {"Error": "Failed to run the recomendation model."}
    
    # Return the shape as a JSON response
    return {"message": "Set up has been completed, now you can safely run the recommendation API."}