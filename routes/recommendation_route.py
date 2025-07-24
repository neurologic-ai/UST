import asyncio
from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from odmantic import AIOEngine
from auth.api_key import get_api_key
from models.fixed_always_reco import AlwaysRecommendProduct, FixedProduct
from models.schema import RecommendationRequestBody
from models.hepler import categories_dct, Aggregation, enrich_with_upc, get_product_names_from_upcs
from db.singleton import get_engine
from repos.fixed_always_product import merge_final_recommendations
from routes.user_route import PermissionChecker
from utils.helper import get_association_recommendations, get_popular_recommendation, load_lookup_dicts
from configs.constant import PROCESSED_DATA_PATH, CATEGORY_DATA_PATH, TIME_SLOTS
from initialize.data_validation import validate
from setup import run_models_and_store_outputs
from fastapi import UploadFile, File
import pandas as pd
from models.db import BreakfastPopular, LunchPopular, DinnerPopular, OtherPopular, BreakfastAssociation, LunchAssociation, DinnerAssociation, OtherAssociation
from initialize.helper import get_timing
import random


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
    processed: UploadFile = File(...), 
    categories: UploadFile = File(...),
    # athorize:bool = Depends(PermissionChecker(['items:read', 'items:write'])),
):
    # if not athorize:
    #         return HTTPException(status_code = 403, detail = "User don't have acess to see the recommendation")
    # Read both files into pandas DataFrames
    df1 = pd.read_csv(processed.file)
    df2 = pd.read_csv(categories.file)
    # Lets see is the input files are in correct format
    validation = validate(df1, df2)
    if not validation:
        print(f"Error: Validation failed, please try again with correct data format.")
        return {"Error": "Validation failed, please try again with correct data format."}

    # Store the input files
    df1.to_csv(PROCESSED_DATA_PATH, index = False)
    df2.to_csv(CATEGORY_DATA_PATH, index = False)
    print("Data is stored successfully")
    try:
        run_models_and_store_outputs()
    except:
        return {"Error": "Failed to run the recomendation model."}
    
    # Return the shape as a JSON response
    return {"message": "Set up has been completed, now you can safely run the recommendation API."}


@router.post("/recommendation")
async def recommendation(
    data: RecommendationRequestBody,
    db: AIOEngine = Depends(get_engine)
):
    final_top_n = data.topN
    top_n = final_top_n + 50

    # === Load Always upfront ===
    always_doc = await db.find_one(AlwaysRecommendProduct)
    always_products = always_doc.products if always_doc else []
    always_upcs = [ap["UPC"] for ap in always_products]

    # === If Always alone is enough ===
    if len(always_upcs) >= final_top_n:
        # Pick a random sample of size N, no repeats
        final_upcs = random.sample(always_upcs, k=final_top_n)

        upc_to_name_map = {ap["UPC"]: ap["Product Name"] for ap in always_products}

        final_result = [{"upc": upc, "name": upc_to_name_map.get(upc, "")} for upc in final_upcs]
        logger.debug("Re Plus Engine No Execute")
        return {
            "message": " Always Recommend used directly",
            "recommendedItems": final_result
        }
    logger.debug("Re Plus Engine Execute")

    name_to_upc_map, upc_to_name_map = load_lookup_dicts()
    cart_items = [upc_to_name_map.get(upc.strip(), "") for upc in data.cartItems]
    current_hr = data.currentHour
    timing_category = get_timing(current_hr, TIME_SLOTS)
    # Gather all recommendations concurrently
    if timing_category == 'Breakfast':
        popular_recommendations, assoc_recommendations  = await asyncio.gather(
            get_popular_recommendation(db, top_n, BreakfastPopular),
            get_association_recommendations(db, cart_items, top_n, BreakfastAssociation)
        )
    elif timing_category == 'Lunch':
        popular_recommendations, assoc_recommendations  = await asyncio.gather(
            get_popular_recommendation(db, top_n, LunchPopular),
            get_association_recommendations(db, cart_items, top_n, LunchAssociation)
        )
    elif timing_category == 'Dinner':
        popular_recommendations, assoc_recommendations  = await asyncio.gather(
            get_popular_recommendation(db, top_n, DinnerPopular),
            get_association_recommendations(db, cart_items, top_n, DinnerAssociation)
        )
    elif timing_category == 'Other':
        popular_recommendations, assoc_recommendations  = await asyncio.gather(
            get_popular_recommendation(db, top_n, OtherPopular),
            get_association_recommendations(db, cart_items, top_n, OtherAssociation)
        )

    aggregator = Aggregation(popular_recommendations, cart_items, categories_dct, current_hr)
    filtered_popular_recommendation = aggregator.get_final_recommendations()

    aggregator = Aggregation(assoc_recommendations, cart_items, categories_dct, current_hr)
    filtered_assoc_recommendation = aggregator.get_final_recommendations()

    base_recommendations = filtered_assoc_recommendation if filtered_assoc_recommendation else filtered_popular_recommendation
    # === Cross-match ===
    base_rec_upcs = [name_to_upc_map.get(name.lower(), "") for name in base_recommendations]
    # logger.debug(base_rec_upcs)

    # === Load Fixed & Always ===
    fixed_doc = await db.find_one(FixedProduct)
    fixed_products = fixed_doc.products if fixed_doc else []

    final_upcs = merge_final_recommendations(base_rec_upcs, fixed_products, always_products, final_top_n)

    final_result = [{"upc": upc, "name": upc_to_name_map.get(upc, "")} for upc in final_upcs]

    return {
        "message": "Final Recommendation",
        "recommendedItems": final_result
    }