import asyncio
import time
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from odmantic import AIOEngine
import redis
from auth.api_key import get_current_tenant
from db.redis_client import get_redis_client
from models.schema import RecommendationRequestBody
from models.hepler import Product, Aggregation
from db.singleton import get_engine
from repos.reco_repos import get_categories_from_cache_or_s3, validate_csv_columns
from utils.file_upload import get_s3_file_url, upload_file_to_s3
from utils.helper import get_association_recommendations, get_popular_recommendation
from configs.constant import TIME_SLOTS
from setup import run_models_and_store_outputs
from fastapi import UploadFile, File
import pandas as pd
from models.db import BreakfastPopular, LunchPopular, DinnerPopular, OtherPopular, BreakfastAssociation, LunchAssociation, DinnerAssociation, OtherAssociation
from initialize.helper import delete_documents_for_tenant_location, get_timing
from utils.save_category_csv import generate_category_df_from_processed
from loguru import logger
import traceback
from initialize.helper import load_lookup_dicts
from weather.api_call import get_weather_feel



def normalize_key(name: str) -> str:
    if not isinstance(name, str):
        return ""
    return name.replace('\xa0', ' ').replace('.', '').replace('$','').strip().lower()
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


async def process_chunk(df_processed, tenantId, locationId):
    try:
        df_processed['Product_name'] = df_processed['Product_name'].map(normalize_key)
        start_time = time.time()
        df_categories, _ = await asyncio.gather(
            generate_category_df_from_processed(df_processed, tenantId, locationId),
            run_models_and_store_outputs(tenantId, locationId, df_processed)
        )
        end_time = time.time()
        logger.debug(f"Time taken for chunk process: {end_time - start_time}")
        return (f"Chunk Done")
    except Exception:
        logger.debug(traceback.format_exc())
        return {"Error": "Failed to complete setup tasks."}



@router.post("/setup")
async def upload_csvs(
    tenantId: str,
    locationId: str,
    processed: UploadFile = File(...),
    db: AIOEngine = Depends(get_engine)
):
    try:
        REQUIRED_COLUMNS = ['Session_id', 'Datetime', 'Product_name','UPC','Quantity','location_id','store_id']  
        # 🔹 Call the validation function
        await validate_csv_columns(processed, REQUIRED_COLUMNS)

        # 🔹 Reset the file pointer after reading it
        processed.file.seek(0)
        processed_url = upload_file_to_s3(processed.file, "processed", tenantId, locationId)

        ###The below code is for local testing.
        # await delete_documents_for_tenant_location(tenantId, locationId)
        
        # CHUNK_SIZE = 10000
        # # List of required columns
        # REQUIRED_COLUMNS = ['Session_id', 'Datetime', 'Product_name','UPC','Quantity','location_id','store_id']  

        # # Step 1: Read both files into pandas DataFrames
        # df_processed_chunks = pd.read_csv(processed.file, chunksize=CHUNK_SIZE, usecols=REQUIRED_COLUMNS, dtype={"UPC": str, "store_id": str})
        # all_tasks = [
        #     process_chunk(df_processed, tenantId, locationId)
        #     for df_processed in df_processed_chunks
        # ]

        # # Run all chunk processes concurrently
        # results = await asyncio.gather(*all_tasks)
        # logger.debug("Data is stored successfully")
        
        # return {
        #     "message": "Sales data has been Uploaded",
            
        # }
    except Exception as e:
        logger.debug(traceback.format_exc())
        raise




@router.post("/recommendation")
async def recommendation(
    data: RecommendationRequestBody,
    # r: redis.Redis = Depends(get_redis_client),
    db: AIOEngine = Depends(get_engine)
    ):
    try:
        current_datetime = data.currentDateTime
        current_hr = data.currentHour
        logger.debug(current_datetime)
        logger.debug(current_hr)

        weather = get_weather_feel(lat=data.latitude, lon=data.longitude,dt=current_datetime)
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
        # print(f"Popular names: {popular_names[:5]}")
        # print(f"Sample from popular_data_dict: {list(popular_data_dict.items())[:3]}")


        assoc_data_dict, assoc_names = await get_association_recommendations(
            db, cart_items, top_n, assoc_model_map[timing_category], filters
        )
        # print(f"association names: {assoc_names[:5]}")
        # print(f"Sample from assoc_data_dict: {list(assoc_data_dict.items())[:3]}")

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

