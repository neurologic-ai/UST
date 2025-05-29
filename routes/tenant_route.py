import secrets
from fastapi import APIRouter, Depends, HTTPException, status
from odmantic import AIOEngine
from bson import ObjectId

from typing import List, Optional

from db.singleton import get_engine
from models.db import Location, Store, Tenant
from models.schema import TenantCreate, TenantUpdate
from routes.user_route import PermissionChecker

router = APIRouter(
    tags=['tenant']
)

def generate_api_key() -> str:
    return secrets.token_urlsafe(32)  # or use any secure token generator

@router.post("/tenant/create")
async def create_tenant(
    data: TenantCreate,
    authorize:bool=Depends(PermissionChecker(['items:write'])),
    db: AIOEngine = Depends(get_engine)
    ):
    existing = await db.find_one(Tenant, Tenant.tenant_name == data.tenant_name)
    if existing:
        raise HTTPException(status_code=400, detail="Tenant with this name already exists")
    
    api_key = generate_api_key()

    tenant = Tenant(
        tenant_name=data.tenant_name,
        api_key=api_key,
        locations=[
            Location(
                location_id=loc.location_id,
                name=loc.name,
                stores=[Store(**store.dict()) for store in loc.stores]
            )
            for loc in data.locations
        ]
    )

    await db.save(tenant)

    return {
        "message": "Tenant created successfully",
        "id": str(tenant.id),
        "api_key": api_key
    }

@router.put("/tenant")
async def update_tenant(
    data: TenantUpdate,
    authorize:bool=Depends(PermissionChecker(['items:write'])),
    db: AIOEngine = Depends(get_engine)
    ):
    tenant = await db.find_one(Tenant, Tenant.id == ObjectId(data.tenant_id))
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant.tenant_name = data.tenant_name
    tenant.locations = [
        Location(
            location_id=loc.location_id,
            name=loc.name,
            stores=[Store(**store.dict()) for store in loc.stores]
        )
        for loc in data.locations
    ]

    await db.save(tenant)
    return {"message": "Tenant updated successfully"}



@router.delete("/tenant/{tenant_id}")
async def delete_tenant(
    tenant_id: str,
    authorize:bool=Depends(PermissionChecker(['items:write'])),
    db: AIOEngine = Depends(get_engine)
    ):
    tenant = await db.find_one(Tenant, Tenant.id == ObjectId(tenant_id))
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    await db.delete(tenant)
    return {"message": "Tenant deleted successfully"}


@router.get("/tenant/{tenant_id}")
async def get_tenant(
    tenant_id: str,
    authorize:bool=Depends(PermissionChecker(['items:read'])),
    db: AIOEngine = Depends(get_engine)
    ):
    try:
        tenant = await db.find_one(Tenant, Tenant.id == ObjectId(tenant_id))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid tenant ID format")

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    return tenant


@router.get("/tenant", response_model=List[Tenant])
async def list_tenants(
    authorize:bool=Depends(PermissionChecker(['items:read'])),
    db: AIOEngine = Depends(get_engine)
    ):
    tenants = [t async for t in db.find(Tenant)]
    return tenants



{
  "locations": [
    {
      "location_id": "location_1",
      "name": "Delhi HQ",
      "stores": [
        {
          "name": "Connaught Place Store",
          "store_id": "store_1"
        },
        {
          "name": "Saket Store",
          "store_id": "store_2"
        }
      ]
    }
      ],
  "tenant_id": "682c16e8cdcefb98ccd4ebe5",
  "tenant_name": "Dominos Updated"
}