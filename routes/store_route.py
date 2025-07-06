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

from db.singleton import get_engine
from models.db import Location, Store, Tenant, User, UserStatus
from models.schema import (
    AddLocationRequest, AddStoreRequest, LocationFilterRequest,
    StoreDisableRequest, StoreEditRequest, StoreFilterRequest
)
from routes.user_route import PermissionChecker
from configs.manager import settings

router = APIRouter(prefix="/api/v2", tags=['store'])


def validate_store_row(row: dict) -> bool:
    required_fields = ["Store ID", "Store Name", "Location Id", "Location"]
    return all(row.get(field) for field in required_fields)


async def parse_csv_file(file: UploadFile) -> List[dict]:
    try:
        content = await file.read()
        return list(csv.DictReader(StringIO(content.decode())))
    except Exception as e:
        logger.error(f"Failed to parse CSV file: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid CSV format: {str(e)}")

async def get_lat_lon(location: str, state: str, country: str, client: httpx.AsyncClient) -> Tuple[Optional[float], Optional[float]]:
    def build_query(parts: List[str]) -> str:
        return " ".join([p for p in parts if p]).strip()

    queries = [
        build_query([location, state, country]),
        build_query([state, country]),
    ]

    for q in queries:
        try:
            url = f"{settings.GEOCODE_BASE_URL}?q={q}&api_key={settings.GEOCODE_API_KEY}"
            logger.debug(f"[Geocode] Trying query: '{q}' -> {url}")
            response = await client.get(url)

            if response.status_code != 200:
                logger.warning(f"[Geocode] Non-200 status: {response.status_code}, body: {response.text}")
                continue

            try:
                results = response.json()
                logger.debug(f"[Geocode] Response: {results}")
            except Exception as parse_error:
                logger.error(f"[Geocode] JSON parse error: {parse_error} | Raw: {response.text}")
                continue

            if results and isinstance(results, list) and results[0]:
                try:
                    lat_raw = results[0].get("lat")
                    lon_raw = results[0].get("lon")

                    if lat_raw is not None and lon_raw is not None:
                        lat = float(lat_raw)
                        lon = float(lon_raw)
                        logger.debug(f"[Geocode] Success: lat={lat}, lon={lon} for query '{q}'")
                        return lat, lon
                    else:
                        logger.warning(f"[Geocode] lat/lon missing in result: {results[0]}")
                except (ValueError, TypeError) as parse_error:
                    logger.warning(f"[Geocode] Failed to convert lat/lon: {parse_error} | Raw: {results[0]}")
        except Exception as e:
            logger.warning(f"[Geocode] Exception for query '{q}': {e}")

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
    tenant_id: str,
    file: UploadFile = File(...),
    authorize: User = Depends(PermissionChecker(['items:write'])),
    db: AIOEngine = Depends(get_engine)
):
    try:
        if not ObjectId.is_valid(tenant_id):
            raise HTTPException(status_code=400, detail="Invalid tenant ID")

        tenant = await db.find_one(Tenant, Tenant.id == ObjectId(tenant_id))
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        csv_rows = await parse_csv_file(file)

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
async def edit_store(data: StoreEditRequest, authorize: User = Depends(PermissionChecker(['items:write'])), db: AIOEngine = Depends(get_engine)):
    try:
        if not ObjectId.is_valid(data.tenant_id):
            raise HTTPException(status_code=400, detail="Invalid tenant ID")
        tenant = await db.find_one(Tenant, Tenant.id == ObjectId(data.tenant_id))
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        for loc in tenant.locations:
            if loc.location_id == data.location_id:
                for store in loc.stores:
                    if store.store_id == data.store_id:
                        if data.name is not None:
                            store.name = data.name
                        if data.state is not None:
                            store.state = data.state
                        if data.country is not None:
                            store.country = data.country
                        if data.lat is None or data.lon is None:
                            async with httpx.AsyncClient() as client:
                                lat, lon = await get_lat_lon(store.name, store.state, store.country, client)
                                store.lat = lat
                                store.lon = lon
                        else:
                            store.lat = data.lat
                            store.lon = data.lon
                        if data.status is not None:
                            store.status = data.status
                        await db.save(tenant)
                        return {"message": "Store updated successfully"}
                raise HTTPException(status_code=404, detail="Store not found")
        raise HTTPException(status_code=404, detail="Location not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/tenant/store/disable")
async def disable_store(data: StoreDisableRequest, authorize: User = Depends(PermissionChecker(['items:write'])), db: AIOEngine = Depends(get_engine)):
    try:
        if not ObjectId.is_valid(data.tenant_id):
            raise HTTPException(status_code=400, detail="Invalid tenant ID")
        tenant = await db.find_one(Tenant, Tenant.id == ObjectId(data.tenant_id))
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        for loc in tenant.locations:
            if loc.location_id == data.location_id:
                for store in loc.stores:
                    if store.store_id == data.store_id:
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
        if not ObjectId.is_valid(filters.tenant_id):
            raise HTTPException(status_code=400, detail="Invalid tenant ID format")

        tenant = await db.find_one(Tenant, Tenant.id == ObjectId(filters.tenant_id))
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        matched_stores = []
        for loc in tenant.locations:
            if filters.location_id and loc.location_id != filters.location_id:
                continue
            for store in loc.stores:
                if filters.store_id and store.store_id != filters.store_id:
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
        if not ObjectId.is_valid(filters.tenant_id):
            raise HTTPException(status_code=400, detail="Invalid tenant ID format")

        tenant = await db.find_one(Tenant, Tenant.id == ObjectId(filters.tenant_id))
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        matched_locations = []
        for loc in tenant.locations:
            if filters.location_id and loc.location_id != filters.location_id:
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
        if not ObjectId.is_valid(data.tenant_id):
            raise HTTPException(status_code=400, detail="Invalid tenant ID format")

        tenant = await db.find_one(Tenant, Tenant.id == ObjectId(data.tenant_id))
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        if any(loc.location_id == data.location_id for loc in tenant.locations):
            raise HTTPException(status_code=400, detail="Location already exists")

        tenant.locations.append(Location(
            location_id=data.location_id,
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
        if not ObjectId.is_valid(data.tenant_id):
            raise HTTPException(status_code=400, detail="Invalid tenant ID format")

        tenant = await db.find_one(Tenant, Tenant.id == ObjectId(data.tenant_id))
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        location = next((loc for loc in tenant.locations if loc.location_id == data.location_id), None)
        if not location:
            raise HTTPException(status_code=404, detail="Location not found")

        if any(store.store_id == data.store_id for store in location.stores):
            raise HTTPException(status_code=400, detail="Store already exists in this location")

        lat, lon = data.lat, data.lon
        if lat is None or lon is None:
            query = " ".join([location.name, data.state or "", data.country or ""]).strip()
            logger.debug(f"[Geocode] Querying for: {query}")
            async with httpx.AsyncClient() as client:
                lat, lon = await get_lat_lon(location.name, data.state, data.country, client)
            logger.debug(f"[Geocode] Result: lat={lat}, lon={lon}")

        location.stores.append(Store(
            store_id=data.store_id,
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
