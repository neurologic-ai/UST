import asyncio
import os
from fastapi import APIRouter, Depends, HTTPException

from odmantic import AIOEngine
from auth.api_key import get_api_key
from models.schema import RecommendationRequestBody
from models.hepler import Aggregation, Product, enrich_with_upc, get_product_names_from_upcs
from db.singleton import get_engine, get_tenant_collections
from routes.user_route import PermissionChecker
from utils.helper import get_association_recommendations, get_popular_recommendation, load_lookup_dicts
from configs.constant import PROCESSED_DATA_PATH, CATEGORY_DATA_PATH, TIME_SLOTS
from initialize.data_validation import validate
from setup import run_models_and_store_outputs
from fastapi import UploadFile, File
import pandas as pd
from models.db import BreakfastPopular, LunchPopular, DinnerPopular, OtherPopular, BreakfastAssociation, LunchAssociation, DinnerAssociation, OtherAssociation
from initialize.helper import get_timing

# router = APIRouter(tags=["Recommendation"])
router = APIRouter(
    prefix="/api/v1",  # version prefix
    tags=["Recommendation V1"],
    dependencies=[Depends(get_api_key)]
)

# @router.get("/view data")
async def get_data(
    db: AIOEngine = Depends(get_engine),
    # athorize:bool = Depends(PermissionChecker(['items:read'])),
):
    # if not athorize:
    #         return HTTPException(status_code = 403, detail = "User don't have acess to see the recommendation")
    data = await db.find(BreakfastPopular)
    return data


@router.post("/setup")
async def upload_csvs(
    tenant: str,
    processed: UploadFile = File(...), 
    categories: UploadFile = File(...)
    # athorize:bool = Depends(PermissionChecker(['items:read', 'items:write'])),
):
    # if not athorize:
    #         return HTTPException(status_code = 403, detail = "User don't have acess to see the recommendation")
    # Read both files into pandas DataFrames
    # Validate tenant name for path safety
    tenant = tenant.replace("/", "_").replace("\\", "_").replace(" ", "_").strip()

    # Create tenant-specific file paths
    processed_path = f"{PROCESSED_DATA_PATH}/{tenant}_processed.csv"
    category_path = f"{CATEGORY_DATA_PATH}/{tenant}_categories.csv"

    df1 = pd.read_csv(processed.file)
    df2 = pd.read_csv(categories.file)
    # Lets see is the input files are in correct format
    validation = validate(df1, df2)
    if not validation:
        print(f"Error: Validation failed, please try again with correct data format.")
        return {"Error": "Validation failed, please try again with correct data format."}

    # Store the input files
    os.makedirs(PROCESSED_DATA_PATH, exist_ok=True)
    os.makedirs(CATEGORY_DATA_PATH, exist_ok=True)
    df1.to_csv(processed_path, index=False)
    df2.to_csv(category_path, index=False)
    print("Data is stored successfully")
    try:
        run_models_and_store_outputs(tenant)
    except:
        return {"Error": "Failed to run the recomendation model."}
    
    # Return the shape as a JSON response
    return {"message": "Set up has been completed, now you can safely run the recommendation API."}


@router.post("/recommendation")
async def recommendation(
    data: RecommendationRequestBody,
    # athorize:bool = Depends(PermissionChecker(['items:read'])),
    db: AIOEngine = Depends(get_engine)
):
    tenant = data.tenant.replace("/", "_").replace("\\", "_").replace(" ", "_").strip() 

    # Create tenant-specific file paths
    category_path = f"{CATEGORY_DATA_PATH}/{tenant}_categories.csv"
    categories_dct = Product(category_path=category_path).load_category_data()
    # if not athorize:
    #     return HTTPException(status_code = 403, detail = "User don't have acess to see the recommendation")
    ######################################
    final_top_n = data.topN
    top_n = final_top_n + 50

    # cart_items = [item.strip().lower() for item in data.cartItems]
    # cart_upcs = data.cartItems
    name_to_upc_map, upc_to_name_map = load_lookup_dicts(tenant)
    cart_items = [upc_to_name_map.get(upc.strip(), "") for upc in data.cartItems]
    # cart_items = get_product_names_from_upcs(cart_upcs)
    current_hr = data.currentHour
    # current_dayofweek = data.current_dayofweek
    # current_weather_category = data.current_weather_category
    # current_holiday = data.current_holiday

    tenant_collections = get_tenant_collections(tenant)
    ######################################
    timing_category = get_timing(current_hr, TIME_SLOTS)
    # Gather all recommendations concurrently
    if timing_category == 'Breakfast':
        popular_recommendations, assoc_recommendations  = await asyncio.gather(
            get_popular_recommendation(tenant_collections["breakfast_popular"], top_n),
            get_association_recommendations(tenant_collections["breakfast_association"], cart_items, top_n)
        )
    elif timing_category == 'Lunch':
        popular_recommendations, assoc_recommendations  = await asyncio.gather(
            get_popular_recommendation(tenant_collections["lunch_popular"], top_n),
            get_association_recommendations(tenant_collections["lunch_association"], cart_items, top_n)
        )
    elif timing_category == 'Dinner':
        popular_recommendations, assoc_recommendations  = await asyncio.gather(
            get_popular_recommendation(tenant_collections["dinner_popular"], top_n),
            get_association_recommendations(tenant_collections["dinner_association"], cart_items, top_n)
        )
    elif timing_category == 'Other':
        popular_recommendations, assoc_recommendations  = await asyncio.gather(
            get_popular_recommendation(tenant_collections["other_popular"], top_n),
            get_association_recommendations(tenant_collections["other_association"], cart_items, top_n)
        )

    aggregator = Aggregation(popular_recommendations, cart_items, categories_dct, current_hr)
    filtered_popular_recommendation = aggregator.get_final_recommendations()

    aggregator = Aggregation(assoc_recommendations, cart_items, categories_dct, current_hr)
    filtered_assoc_recommendation = aggregator.get_final_recommendations()

    # if len(filtered_assoc_recommendation) == 0:
    #     final_recommendation = {"message" : "Popular Recommendation", "recommendedItems": filtered_popular_recommendation[:final_top_n]}
    # else:
    #     final_recommendation = {"message" : "Association Recommendation", "recommendedItems": filtered_assoc_recommendation[:final_top_n]}
    if len(filtered_assoc_recommendation) == 0:
        final_recommendation = {
            "message": "Popular Recommendation",
            "recommendedItems": enrich_with_upc(filtered_popular_recommendation[:final_top_n], name_to_upc_map)
        }
    else:
        final_recommendation = {
            "message": "Association Recommendation",
            "recommendedItems": enrich_with_upc(filtered_assoc_recommendation[:final_top_n], name_to_upc_map)
        }
    return final_recommendation