import asyncio
import csv
from datetime import datetime
from io import StringIO
import traceback
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from loguru import logger
from odmantic import AIOEngine
from bson import ObjectId
from typing import List, Optional, Tuple
import httpx

from auth.tenant_user_verify import check_user_role_and_status
from db.singleton import get_engine
from models.db import Location, Store, Tenant, User, UserRole, UserStatus
from models.schema import (
    AddLocationRequest, AddStoreRequest, LocationFilterRequest,
    StoreDisableRequest, StoreEditRequest, StoreFilterRequest
)
from routes.user_route import PermissionChecker
from configs.manager import settings

router = APIRouter(prefix="/api/v2", tags=['store'])

required_fields = ["Store ID", "Store Name", "Location Id", "Location", "Country","State"]

# def validate_store_row(row: dict) -> bool:
#     return all(row.get(field) for field in required_fields)
def validate_store_row(row: dict) -> list[str]:
    """Return list of missing/empty fields, [] if valid."""
    return [f for f in required_fields if not row.get(f) or not row[f].strip()]


async def parse_csv_file(file: UploadFile) -> List[dict]:
    try:
        content = await file.read()
        decoded = content.decode()
        reader = csv.DictReader(StringIO(decoded))

        # ✅ Check if required headers are present
        missing = [col for col in required_fields if col not in reader.fieldnames]
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"CSV is missing required columns: {', '.join(missing)}"
            )

        return list(reader)
    except Exception as e:
        logger.error(f"Failed to parse CSV file: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid CSV format: {str(e)}")

async def get_lat_lon(location: str, state: str, country: str, client: httpx.AsyncClient) -> Tuple[Optional[float], Optional[float]]:
    def build_query(parts: List[str]) -> str:
        return " ".join([p for p in parts if p]).strip()

    queries = [
        build_query([location, state, country]),
        build_query([state, country]),
        build_query([country]),
    ]

    for q in queries:
        try:
            url = f"{settings.GEOCODE_BASE_URL}?q={q}&api_key={settings.GEOCODE_API_KEY}"
            logger.debug(f"[Geocode] Trying query: '{q}' -> {url}")
            response = await client.get(url)

            if response.status_code != 200:
                logger.warning(f"[Geocode] Non-200 status: {response.status_code}, body: {response.text}")
                await asyncio.sleep(1)
                continue

            try:
                results = response.json()
            except Exception as parse_error:
                logger.error(f"[Geocode] JSON parse error: {parse_error} | Raw: {response.text}")
                await asyncio.sleep(1)
                continue

            if results and isinstance(results, list) and results[0]:
                logger.debug(results)
                lat_raw = results[0].get("lat")
                lon_raw = results[0].get("lon")

                if lat_raw is not None and lon_raw is not None:
                    lat = float(lat_raw)
                    lon = float(lon_raw)
                    logger.debug(f"[Geocode] Success: lat={lat}, lon={lon} for query '{q}'")
                    return lat, lon
                else:
                    logger.warning(f"[Geocode] lat/lon missing in result: {results[0]}")
        except Exception as e:
            logger.warning(f"[Geocode] Exception for query '{q}': {e}")

        # Wait before trying the next query
        logger.debug(f"[Geocode] Waiting 1 second before next query...")
        await asyncio.sleep(1)

    logger.warning(f"[Geocode] All attempts failed for location='{location}', state='{state}', country='{country}'")
    return None, None

async def process_row(row: dict, tenant: Tenant, client: httpx.AsyncClient) -> bool:
    try:
        if not validate_store_row(row):
            logger.warning(f"Missing required fields in row: {row}")
            return False

        location_id = row["Location Id"].strip()
        location_name = row["Location"].strip()
        store_id = row["Store ID"].strip()
        store_name = row["Store Name"].strip()
        country = row.get("Country", "").strip()
        state = row.get("State", "").strip()

        lat, lon = await get_lat_lon(location_name, state, country, client)

        store_data = Store(
            store_id=store_id,
            name=store_name,
            status=UserStatus.ACTIVE,
            state=state,
            country=country,
            lat=lat,
            lon=lon
        )

        location = next((loc for loc in tenant.locations if loc.location_id == location_id), None)
        if location:
            if not any(s.store_id == store_id for s in location.stores):
                location.stores.append(store_data)
                return True
        else:
            tenant.locations.append(Location(
                location_id=location_id,
                name=location_name,
                status=UserStatus.ACTIVE,
                stores=[store_data]
            ))
            return True

    except Exception as e:
        logger.error(f"Error processing row {row}: {e}")
    return False


@router.post("/tenant/stores/upload")
async def upload_stores_from_csv(
    tenantId: str,
    file: UploadFile = File(...),
    authorize: User = Depends(PermissionChecker(['items:write'])),
    db: AIOEngine = Depends(get_engine)
):
    try:
        if not ObjectId.is_valid(tenantId):
            raise HTTPException(status_code=400, detail="Invalid tenant ID")
        
        check_user_role_and_status(authorize, tenantId)

        tenant = await db.find_one(Tenant, Tenant.id == ObjectId(tenantId))
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        # csv_rows = await parse_csv_file(file)
        # invalid_rows = [row for row in csv_rows if not validate_store_row(row)]
        # if invalid_rows:
        #     raise HTTPException(
        #         status_code=400,
        #         detail=f"CSV contains {len(invalid_rows)} row(s) with missing required fields: {', '.join(['Store ID', 'Store Name', 'Location Id', 'Location'])}"
        #     )
        csv_rows = await parse_csv_file(file)

        errors = []
        for i, row in enumerate(csv_rows, start=2):  # start=2, since row 1 = headers
            missing = validate_store_row(row)
            if missing:
                errors.append({"row": i, "missing_fields": missing})

        if errors:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": f"CSV contains {len(errors)} invalid row(s).",
                    "errors": errors
                }
            )

        updated = False
        async with httpx.AsyncClient() as client:
            for row in csv_rows:
                changed = await process_row(row, tenant, client)
                if changed:
                    updated = True

        if updated:
            await db.save(tenant)
            return {"message": "Stores uploaded and saved successfully."}
        return {"message": "No updates made. All records already exist."}

    except HTTPException:
        raise
    except Exception as e:
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/tenant/store/edit")
async def edit_store(
    data: StoreEditRequest,
    authorize: User = Depends(PermissionChecker(['items:write'])),
    db: AIOEngine = Depends(get_engine)
):
    try:
        if not ObjectId.is_valid(data.tenantId):
            raise HTTPException(status_code=400, detail="Invalid tenant ID")
        
        check_user_role_and_status(authorize, data.tenantId)

        tenant = await db.find_one(Tenant, Tenant.id == ObjectId(data.tenantId))
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        # Locate the correct location
        location = next((loc for loc in tenant.locations if loc.location_id == data.locationId), None)
        if not location:
            raise HTTPException(status_code=404, detail="Location not found")

        # Locate the correct store
        store = next((s for s in location.stores if s.store_id == data.storeId), None)
        if not store:
            raise HTTPException(status_code=404, detail="Store not found")

        updated = False

        if data.name is not None:
            if not data.name.strip():
                raise HTTPException(status_code=400, detail="Store name cannot be empty")
            store.name = data.name.strip()
            updated = True

        if data.state is not None:
            if not data.state.strip():
                raise HTTPException(status_code=400, detail="State cannot be empty")
            store.state = data.state.strip()
            updated = True

        if data.country is not None:
            if not data.country.strip():
                raise HTTPException(status_code=400, detail="Country cannot be empty")
            store.country = data.country.strip()
            updated = True

        if data.lat is None or data.lon is None:
            async with httpx.AsyncClient() as client:
                lat, lon = await get_lat_lon(location.name, store.state, store.country, client)
                store.lat = lat
                store.lon = lon
            updated = True
        else:
            store.lat = data.lat
            store.lon = data.lon
            updated = True

        if data.status is not None:
            store.status = data.status
            updated = True

        if not updated:
            raise HTTPException(status_code=400, detail="No fields provided to update")

        await db.save(tenant)

        return {"message": "Store updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/tenant/store/disable")
async def disable_store(data: StoreDisableRequest, authorize: User = Depends(PermissionChecker(['items:write'])), db: AIOEngine = Depends(get_engine)):
    try:
        if not ObjectId.is_valid(data.tenantId):
            raise HTTPException(status_code=400, detail="Invalid tenant ID")
        
        check_user_role_and_status(authorize, data.tenantId)

        tenant = await db.find_one(Tenant, Tenant.id == ObjectId(data.tenantId))
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        for loc in tenant.locations:
            if loc.location_id == data.locationId:
                for store in loc.stores:
                    if store.store_id == data.storeId:
                        if store.status == UserStatus.INACTIVE:
                            return {"message": "Store is already inactive"}
                        store.status = UserStatus.INACTIVE
                        tenant.updated_at = datetime.utcnow()
                        tenant.updated_by = str(authorize.id)
                        await db.save(tenant)
                        return {"message": "Store disabled successfully"}
                raise HTTPException(status_code=404, detail="Store not found")
        raise HTTPException(status_code=404, detail="Location not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/tenant/stores/list")
async def list_stores(
    filters: StoreFilterRequest,
    authorize: User = Depends(PermissionChecker(['items:read'])),
    db: AIOEngine = Depends(get_engine)
):
    try:
        if not ObjectId.is_valid(filters.tenantId):
            raise HTTPException(status_code=400, detail="Invalid tenant ID")
        check_user_role_and_status(authorize, filters.tenantId)

        tenant = await db.find_one(Tenant, Tenant.id == ObjectId(filters.tenantId))
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        matched_stores = []
        for loc in tenant.locations:
            if filters.locationId and loc.location_id != filters.locationId:
                continue
            for store in loc.stores:
                if filters.storeId and store.store_id != filters.storeId:
                    continue
                if filters.status and store.status != filters.status:
                    continue
                matched_stores.append({
                    "location_id": loc.location_id,
                    "location_name": loc.name,
                    **store.dict()
                })
        return matched_stores

    except HTTPException:
        raise
    except Exception as e:
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/tenant/locations/list")
async def list_locations(
    filters: LocationFilterRequest,
    authorize: User = Depends(PermissionChecker(['items:read'])),
    db: AIOEngine = Depends(get_engine)
):
    try:
        if not ObjectId.is_valid(filters.tenantId):
            raise HTTPException(status_code=400, detail="Invalid tenant ID")
        check_user_role_and_status(authorize, filters.tenantId)
        tenant = await db.find_one(Tenant, Tenant.id == ObjectId(filters.tenantId))
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        matched_locations = []
        for loc in tenant.locations:
            if filters.locationId and loc.location_id != filters.locationId:
                continue
            if filters.status and loc.status != filters.status:
                continue
            matched_locations.append(loc)

        return matched_locations

    except HTTPException:
        raise
    except Exception as e:
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/tenant/location/add")
async def add_location(
    data: AddLocationRequest,
    authorize: User = Depends(PermissionChecker(['items:write'])),
    db: AIOEngine = Depends(get_engine)
):
    try:
        if not ObjectId.is_valid(data.tenantId):
            raise HTTPException(status_code=400, detail="Invalid tenant ID")

        check_user_role_and_status(authorize, data.tenantId)

        tenant = await db.find_one(Tenant, Tenant.id == ObjectId(data.tenantId))
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        if not data.locationId or not data.locationId.strip():
            raise HTTPException(status_code=400, detail="Location ID is required and cannot be empty")

        if not data.name or not data.name.strip():
            raise HTTPException(status_code=400, detail="Location name is required and cannot be empty")

        if any(loc.location_id == data.locationId for loc in tenant.locations):
            raise HTTPException(status_code=400, detail="Location already exists")

        tenant.locations.append(Location(
            location_id=data.locationId,
            name=data.name,
            status=data.status,
            stores=[]
        ))

        await db.save(tenant)
        return {"message": "Location added successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/tenant/store/add")
async def add_store(
    data: AddStoreRequest,
    authorize: User = Depends(PermissionChecker(['items:write'])),
    db: AIOEngine = Depends(get_engine)
):
    try:
        if not ObjectId.is_valid(data.tenantId):
            raise HTTPException(status_code=400, detail="Invalid tenant ID")

        check_user_role_and_status(authorize, data.tenantId)

        tenant = await db.find_one(Tenant, Tenant.id == ObjectId(data.tenantId))
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        if not data.storeId or not data.storeId.strip():
            raise HTTPException(status_code=400, detail="Store ID is required and cannot be empty")
        if not data.locationId or not data.locationId.strip():
            raise HTTPException(status_code=400, detail="Location ID is required and cannot be empty")


        location = next((loc for loc in tenant.locations if loc.location_id == data.locationId), None)
        if not location:
            raise HTTPException(status_code=404, detail="Location not found")

        if any(store.store_id == data.storeId for store in location.stores):
            raise HTTPException(status_code=400, detail="Store already exists in this location")
        # Validate essential string fields
        if not data.name or not data.name.strip():
            raise HTTPException(status_code=400, detail="Store name is required and cannot be empty")

        if not data.state or not data.state.strip():
            raise HTTPException(status_code=400, detail="State is required and cannot be empty")

        if not data.country or not data.country.strip():
            raise HTTPException(status_code=400, detail="Country is required and cannot be empty")


        lat, lon = data.lat, data.lon
        if lat is None or lon is None:
            query = " ".join([location.name, data.state or "", data.country or ""]).strip()
            logger.debug(f"[Geocode] Querying for: {query}")
            async with httpx.AsyncClient() as client:
                lat, lon = await get_lat_lon(location.name, data.state, data.country, client)
            logger.debug(f"[Geocode] Result: lat={lat}, lon={lon}")

        location.stores.append(Store(
            store_id=data.storeId,
            name=data.name,
            status=data.status,
            state=data.state,
            country=data.country,
            lat=lat,
            lon=lon
        ))

        await db.save(tenant)
        return {"message": "Store added successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")
