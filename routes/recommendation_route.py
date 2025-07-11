import asyncio
from datetime import datetime
import time
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from odmantic import AIOEngine, ObjectId
import redis.asyncio as redis
from auth.api_key import get_current_tenant
from auth.tenant_user_verify import check_user_role_and_status
from db.redis_client import get_redis_client
from models.schema import RecommendationRequestBody
from models.hepler import Product, Aggregation
from db.singleton import get_engine
from repos.reco_repos import get_categories_for_products, get_categories_from_cache_or_s3, validate_csv_columns
from routes.user_route import PermissionChecker
from utils.file_upload import upload_file_to_s3
from utils.helper import get_association_recommendations, get_popular_recommendation
from configs.constant import TIME_SLOTS
from setup import run_models_and_store_outputs
from fastapi import UploadFile, File
import pandas as pd
from models.db import BreakfastPopular, LunchPopular, DinnerPopular, OtherPopular, BreakfastAssociation, LunchAssociation, DinnerAssociation, OtherAssociation, Tenant
from initialize.helper import delete_documents_for_tenant_location_and_store_ids, get_timing
from utils.save_category_csv import generate_category_df_from_processed
from loguru import logger
import traceback
from initialize.helper import load_lookup_dicts
from weather.api_call import get_weather_feel
import json
import zipfile
import io
import base64


def normalize_key(name: str) -> str:
    if not isinstance(name, str):
        return ""
    return name.replace('\xa0', ' ').replace('.', '').replace('$','').strip().lower()
# router = APIRouter(tags=["Recommendation"])
router = APIRouter(
    prefix="/api/v2",  # version prefix
    tags=["Recommendation V2"]
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
    authorize: bool = Depends(PermissionChecker(['items:write'])),
    db: AIOEngine = Depends(get_engine)
):
    try:
        logger.debug("API call started")

        if not ObjectId.is_valid(tenantId):
            raise HTTPException(status_code=400, detail="Invalid tenant ID")
        
        check_user_role_and_status(authorize, tenantId)

        tenant = await db.find_one(Tenant, Tenant.id == ObjectId(tenantId))
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        location = next((loc for loc in tenant.locations if loc.location_id == locationId), None)
        if not location:
            raise HTTPException(status_code=404, detail=f"Location '{locationId}' not found for this tenant")
        
        REQUIRED_COLUMNS = ['Session_id', 'Datetime', 'Product_name','UPC','Quantity','location_id','store_id']  
        await validate_csv_columns(processed, REQUIRED_COLUMNS)
        processed.file.seek(0)

        logger.debug("Extracting store_ids and location_ids from CSV...")
        start_time = time.perf_counter()

        store_ids_in_location = {store.store_id for store in location.stores}
        uploaded_store_ids = set()
        uploaded_location_ids = set()

        for chunk in pd.read_csv(
            processed.file,
            usecols=["store_id", "location_id"],
            chunksize=100_000,
            dtype={"store_id": str, "location_id": str}
        ):
            uploaded_store_ids.update(chunk["store_id"].dropna().unique().tolist())
            uploaded_location_ids.update(chunk["location_id"].dropna().unique().tolist())

        invalid_store_ids = [sid for sid in uploaded_store_ids if sid not in store_ids_in_location]

        invalid_location_ids = uploaded_location_ids - {locationId}  

        error_messages = []
        
        if invalid_location_ids:
            error_messages.append(f"Invalid location_id(s): {', '.join(invalid_location_ids)}. Expected only: {locationId}")
        if invalid_store_ids:
            error_messages.append(f"Invalid store_id(s): {', '.join(invalid_store_ids)}")

        if error_messages:
            raise HTTPException(
                status_code=400,
                detail="; ".join(error_messages)
            )


        end_time = time.perf_counter()
        logger.debug(f"Validated store_ids and location_id in {end_time - start_time:.2f} seconds")

        processed.file.seek(0)  # Reset before upload
        processed_url = upload_file_to_s3(processed.file, "processed", tenantId, locationId, store_ids=uploaded_store_ids)

        return {
            "message": "Sales data has been uploaded successfully",
            "storeCSount": len(uploaded_store_ids)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/recommendation")
async def recommendation(
    data: RecommendationRequestBody,
    r: redis.Redis = Depends(get_redis_client),
    db: AIOEngine = Depends(get_engine),
    tenant: Tenant = Depends(get_current_tenant)
    ):
    try:
        start_time = time.perf_counter()
        current_hr = data.currentHour
        current_datetime = datetime.utcnow()
        tenant_id = str(tenant.id)

        logger.debug(current_datetime)
        logger.debug(current_hr)
        logger.debug(tenant_id)
        if not (0 <= data.currentHour <= 23):
            raise HTTPException(status_code=400, detail="currentHour must be between 0 and 23")

        # Validate location
        location = next((loc for loc in tenant.locations if loc.location_id == data.locationId), None)
        if not location:
            raise HTTPException(status_code=400, detail=f"Invalid location_id: {data.locationId}")

        # Validate store
        store = next((s for s in location.stores if s.store_id == data.storeId), None)
        if not store:
            raise HTTPException(status_code=400, detail=f"Invalid store_id: {data.storeId}")

        if store.lat is None or store.lon is None:
            raise HTTPException(status_code=400, detail="Store does not have lat/lon info")

        # Get weather using store coordinates
        weather = await get_weather_feel(lat=store.lat, lon=store.lon, dt=current_datetime, redis_client=r)
        # weather = "moderate"
        logger.debug(weather)
        # Load lookup dictionaries for the given tenant and location
        name_to_upc, upc_to_name = await load_lookup_dicts(tenant_id, data.locationId)

        if not name_to_upc or not upc_to_name:
            return JSONResponse(
                status_code=404,
                content={"message": "Lookup dictionaries not found for given tenant and location."}
            )

        final_top_n = data.topN
        top_n = final_top_n + 50


        # current_hr = data.currentHour
        ######################################
        timing_category = get_timing(current_hr, TIME_SLOTS)
        logger.debug(timing_category)
        
        filters = {
            "tenant_id": tenant_id,
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
        # Run both functions concurrently
        (popular_result, assoc_result) = await asyncio.gather(
            get_popular_recommendation(
                db, top_n, popular_model_map[timing_category], filters
            ),
            get_association_recommendations(
                db, cart_items, top_n, assoc_model_map[timing_category], filters
            )
        )

        popular_data_dict, popular_names = popular_result
        assoc_data_dict, assoc_names = assoc_result
        all_required_names = set(popular_names + assoc_names + cart_items)
        categories_dct = await get_categories_for_products(list(all_required_names), tenant_id, data.locationId, db)

        # ✅ Define helper function locally
        async def run_aggregation(name_list, cart_items, categories, current_hr, weather):
            aggregator = Aggregation(name_list, cart_items, categories, current_hr, weather)
            return aggregator.get_final_recommendations()

        # ✅ Run both aggregations concurrently
        filtered_popular_names, filtered_assoc_names = await asyncio.gather(
            run_aggregation(popular_names, cart_items, categories_dct, current_hr, weather),
            run_aggregation(assoc_names, cart_items, categories_dct, current_hr, weather),
        )


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
        end_time = time.perf_counter()
        logger.debug(f"start_time: {start_time}")
        logger.debug(f"end_time: {end_time}")
        logger.debug(f"elapsed: {end_time - start_time:.3f} seconds")


        return final_recommendation
    except:
        logger.debug(traceback.format_exc())
        raise