import asyncio
from collections import defaultdict
from datetime import datetime
from io import BytesIO, StringIO
import pickle
from fastapi import APIRouter, Depends, HTTPException

from fastapi.responses import JSONResponse
from odmantic import AIOEngine
import redis
from auth.api_key import get_current_tenant
from db.redis_client import get_redis_client
from models.schema import RecommendationRequestBody
from models.hepler import Product, Aggregation
from db.singleton import get_engine
from repos.reco_repos import get_categories_from_cache_or_s3, get_product_names_from_upcs
from utils.file_download import download_file_from_s3
from utils.file_upload import get_s3_file_url, upload_file_to_s3
from utils.helper import get_association_recommendations, get_popular_recommendation
from configs.constant import TIME_SLOTS
from setup import run_models_and_store_outputs
from fastapi import UploadFile, File
import pandas as pd
from models.db import BreakfastPopular, LunchPopular, DinnerPopular, OtherPopular, BreakfastAssociation, LunchAssociation, DinnerAssociation, OtherAssociation
from initialize.helper import get_timing
from utils.save_category_csv import generate_category_df_from_processed
from loguru import logger
import traceback
from initialize.helper import load_lookup_dicts
from weather.api_call import get_weather_feel
# router = APIRouter(tags=["Recommendation"])
router = APIRouter(
    prefix="/api/v2",  # version prefix
    tags=["Recommendation V2"],
    dependencies=[Depends(get_current_tenant)]
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
    tenantId: str,
    locationId: str,
    processed: UploadFile = File(...),
    r: redis.Redis = Depends(get_redis_client)
):
    try:
        # Step 1: Read both files into pandas DataFrames
        df_processed = pd.read_csv(processed.file)
        processed.file.seek(0)

        # Step 2: Generate category data dynamically
        df_categories = generate_category_df_from_processed(df_processed,r)

        # Save categories to in-memory buffer for S3 upload
        categories_buffer = BytesIO()
        categories_buffer.write(df_categories.to_csv(index=False).encode('utf-8'))
        categories_buffer.seek(0)


        processed_url = upload_file_to_s3(processed.file, "processed", tenantId, locationId)
        categories_url = upload_file_to_s3(categories_buffer, "categories", tenantId, locationId)
        # print("Data is stored successfully")
        try:
            run_models_and_store_outputs(processed_url, tenantId, locationId)
        except:
            logger.debug(traceback.format_exc())
            return {"Error": "Failed to run the recomendation model."}
        return {
            "message": "Setup completed. You can now safely run the recommendation API.",
            "processed_file_url": processed_url,
            "categories_file_url": "categories_url"
        }
    except Exception as e:
        logger.debug(traceback.format_exc())




@router.post("/recommendation")
async def recommendation(
    data: RecommendationRequestBody,
    r: redis.Redis = Depends(get_redis_client),
    db: AIOEngine = Depends(get_engine)
    ):
    try:
        current_datetime = data.currentDateTime
        current_hr = data.currentHour
        logger.debug(current_datetime)
        logger.debug(current_hr)

        weather = get_weather_feel(lat=data.latitude, lon=data.longitude,dt=current_datetime, redis_client=r)
        logger.debug(weather)

        s3_url = get_s3_file_url("categories", data.tenantId, data.locationId)
        categories_dct = await get_categories_from_cache_or_s3(data.tenantId, data.locationId, s3_url, db)

        final_top_n = data.topN
        top_n = final_top_n + 50

        # Load lookup dictionaries for the given tenant and location
        name_to_upc, upc_to_name = await load_lookup_dicts(data.tenantId, data.locationId)

        if not name_to_upc or not upc_to_name:
            return JSONResponse(
                status_code=404,
                content={"message": "Lookup dictionaries not found for given tenant and location."}
            )


        # current_hr = data.currentHour
        ######################################
        timing_category = get_timing(current_hr, TIME_SLOTS)
        logger.debug(timing_category)
        
        filters = {
            "tenant_id": data.tenantId,
            "location_id": data.locationId,
            "store_id": data.storeId
            # "timing": timing_category
        }
        popular_model_map = {
            'Breakfast': BreakfastPopular,
            'Lunch': LunchPopular,
            'Dinner': DinnerPopular,
            'Other': OtherPopular
        }

        assoc_model_map = {
            'Breakfast': BreakfastAssociation,
            'Lunch': LunchAssociation,
            'Dinner': DinnerAssociation,
            'Other': OtherAssociation
        }
        # UPC → product name
        cart_items = [name.lower() for name in (upc_to_name.get(upc) for upc in data.cartItems) if name]

        print(f"Cart UPCs: {data.cartItems}")
        print(f"Cart product names from UPCs: {cart_items}")


        popular_data_dict, popular_names = await get_popular_recommendation(
        db, top_n, popular_model_map[timing_category], filters
        )
        print(f"Popular names: {popular_names[:5]}")
        print(f"Sample from popular_data_dict: {list(popular_data_dict.items())[:3]}")


        assoc_data_dict, assoc_names = await get_association_recommendations(
            db, cart_items, top_n, assoc_model_map[timing_category], filters
        )
        print(f"association names: {assoc_names[:5]}")
        print(f"Sample from assoc_data_dict: {list(assoc_data_dict.items())[:3]}")

        aggregator = Aggregation(popular_names, cart_items, categories_dct, current_hr, weather)
        filtered_popular_names = aggregator.get_final_recommendations()

        aggregator = Aggregation(assoc_names, cart_items, categories_dct, current_hr, weather)
        filtered_assoc_names = aggregator.get_final_recommendations()

        if filtered_assoc_names:
            final_recommendation = {
                "message": "Association Recommendation",
                "recommendedItems": [
                    {
                        "name": name,
                        "upc": assoc_data_dict[name].upc
                    }
                    for name in filtered_assoc_names
                    if name in assoc_data_dict
                ][:data.topN]
            }
        else:
            final_recommendation = {
                "message": "Popular Recommendation",
                "recommendedItems": [
                    {
                        "name": name,
                        "upc": popular_data_dict[name].upc
                    }
                    for name in filtered_popular_names
                    if name in popular_data_dict
                ][:data.topN]
            }

        return final_recommendation
    except:
        logger.debug(traceback.format_exc())
