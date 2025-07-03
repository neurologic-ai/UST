import csv
from datetime import datetime
from io import StringIO
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from loguru import logger
from odmantic import AIOEngine
from bson import ObjectId
from typing import List, Optional
from db.singleton import get_engine
from models.db import Location, Store, Tenant, UserStatus
from models.schema import AddLocationRequest, AddStoreRequest, LocationFilterRequest, StoreDisableRequest, StoreEditRequest, StoreFilterRequest, TenantCreate, TenantUpdate
from routes.user_route import PermissionChecker
import csv
from io import StringIO
from typing import Optional, Tuple
from fastapi import UploadFile, File, HTTPException, Depends
from odmantic import AIOEngine
from bson import ObjectId
import httpx
from configs.manager import settings

router = APIRouter(
    prefix="/api/v2",
    tags=['store']
)

async def parse_csv_file(file: UploadFile) -> list[dict]:
    """Read and parse the CSV into a list of dict rows."""
    content = await file.read()
    try:
        return list(csv.DictReader(StringIO(content.decode())))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid CSV format: {str(e)}")


async def get_lat_lon(location: str, state: str, country: str, client: httpx.AsyncClient) -> Tuple[Optional[float], Optional[float]]:
    """Try geocoding with full and partial query inputs, return (lat, lon) or (None, None)."""
    def build_query(parts: List[str]) -> str:
        return " ".join([p for p in parts if p]).strip()

    queries = [
        build_query([location, state, country]),  # full
        build_query([state, country]),            # fallback
    ]

    for q in queries:
        try:
            url = f"{settings.GEOCODE_BASE_URL}?q={q}&api_key={settings.GEOCODE_API_KEY}"
            logger.debug(f"[Geocode] Trying query: '{q}'")
            response = await client.get(url)
            if response.status_code == 200:
                results = response.json()
                if results:
                    lat = float(results[0].get("lat"))
                    lon = float(results[0].get("lon"))
                    logger.debug(f"[Geocode] Success: lat={lat}, lon={lon} for query '{q}'")
                    return lat, lon
        except Exception as e:
            logger.warning(f"[Geocode] Exception for query '{q}': {e}")

    logger.warning(f"[Geocode] All attempts failed for location='{location}', state='{state}', country='{country}'")
    return None, None


async def process_row(row: dict, tenant: Tenant, client: httpx.AsyncClient) -> bool:
    """Process one row from the CSV: update or add location/store."""
    if not row.get("Store ID") or not row.get("Location Id"):
        return False

    location_id = row["Location Id"].strip()
    location_name = row["Location"].strip()
    store_id = row["Store ID"].strip()
    store_name = row["Store Name"].strip()
    country = row.get("Country", "").strip()
    state = row.get("State", "").strip()

    # Compose query and get lat/lon
    lat, lon = await get_lat_lon(location_name, state, country, client)


    # Create new store
    store_data = Store(
        store_id=store_id,
        name=store_name,
        status=UserStatus.ACTIVE,
        state=state,
        country=country,
        lat=lat,
        lon=lon
    )

    # Append or update in the tenant
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

    return False


@router.post("/tenant/stores/upload")
async def upload_stores_from_csv(
    tenant_id: str,
    file: UploadFile = File(...),
    authorize: bool = Depends(PermissionChecker(['items:write'])),
    db: AIOEngine = Depends(get_engine)
):
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


@router.put("/tenant/store/edit")
async def edit_store(
    data: StoreEditRequest,
    authorize: bool = Depends(PermissionChecker(['items:write'])),
    db: AIOEngine = Depends(get_engine)
):
    tenant = await db.find_one(Tenant, Tenant.id == ObjectId(data.tenant_id))
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    for loc in tenant.locations:
        if loc.location_id == data.location_id:
            for store in loc.stores:
                if store.store_id == data.store_id:
                    # Apply only non-null updates
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


@router.put("/tenant/store/disable")
async def disable_store(
    data: StoreDisableRequest,
    authorize: bool = Depends(PermissionChecker(['items:write'])),
    db: AIOEngine = Depends(get_engine)
):
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


@router.post("/tenant/stores/list")
async def list_stores(
    filters: StoreFilterRequest,
    authorize: bool = Depends(PermissionChecker(['items:read'])),
    db: AIOEngine = Depends(get_engine)
):
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


@router.post("/tenant/locations/list")
async def list_locations(
    filters: LocationFilterRequest,
    authorize: bool = Depends(PermissionChecker(['items:read'])),
    db: AIOEngine = Depends(get_engine)
):
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



@router.post("/tenant/location/add")
async def add_location(
    data: AddLocationRequest,
    authorize: bool = Depends(PermissionChecker(['items:write'])),
    db: AIOEngine = Depends(get_engine)
):
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


@router.post("/tenant/store/add")
async def add_store(
    data: AddStoreRequest,
    authorize: bool = Depends(PermissionChecker(['items:write'])),
    db: AIOEngine = Depends(get_engine)
):
    tenant = await db.find_one(Tenant, Tenant.id == ObjectId(data.tenant_id))
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    location = next((loc for loc in tenant.locations if loc.location_id == data.location_id), None)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    if any(store.store_id == data.store_id for store in location.stores):
        raise HTTPException(status_code=400, detail="Store already exists in this location")

    lat, lon = data.lat, data.lon

    # If lat/lon not provided, fetch via geocode
    if lat is None or lon is None:
        query = " ".join([location.name, data.state or "", data.country or ""]).strip()
        logger.debug(f"[Geocode] Querying for: {query}")
        async with httpx.AsyncClient() as client:
            lat, lon = await get_lat_lon(query, client)
        logger.debug(f"[Geocode] Result: lat={lat}, lon={lon}")

    # Append new store
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
