from datetime import datetime
import secrets
from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from odmantic import AIOEngine
from bson import ObjectId
from bson.regex import Regex
from typing import List, Optional

from db.singleton import get_engine
from models.db import Location, Store, Tenant, UserStatus
from models.schema import TenantCreate, TenantFilterRequest, TenantUpdate
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
    normalized_name = data.tenantName.strip().lower()
    existing = await db.find_one(Tenant, Tenant.normalized_name == normalized_name)
    if existing:
        raise HTTPException(status_code=400, detail="Tenant with this name already exists")
    
    if not data.apiKey:
        api_key = generate_api_key()
    else:
        api_key = data.apiKey

    tenant = Tenant(
        tenant_name=data.tenantName,
        normalized_name=normalized_name,
        api_key=api_key,
        locations=[],
        created_at= datetime.utcnow(),
        created_by=str(authorize.id),
        updated_at=None,
        updated_by=None,
        status=data.status
    )

    await db.save(tenant)

    return {
        "message": "Tenant created successfully",
        "id": str(tenant.id),
        "tenantName": tenant.tenant_name,
        "apiKey": api_key
    }

@router.put("/tenant/update")
async def update_tenant(
    data: TenantUpdate,
    authorize: bool = Depends(PermissionChecker(['items:write'])),
    db: AIOEngine = Depends(get_engine)
):
    tenant = await db.find_one(Tenant, Tenant.id == ObjectId(data.tenant_id))
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    normalized_name = data.tenant_name.strip().lower()
    
    # Check for normalized name conflict with another tenant
    existing = await db.find_one(
        Tenant, 
        (Tenant.normalized_name == normalized_name) & (Tenant.id != tenant.id)
    )
    if existing:
        raise HTTPException(status_code=400, detail="Another tenant with this name already exists")

    tenant.tenant_name = data.tenant_name
    tenant.normalized_name = normalized_name
    tenant.api_key = data.api_key
    tenant.status = data.status
    tenant.updated_at = datetime.utcnow()
    tenant.updated_by = str(authorize.id)

    await db.save(tenant)
    return {"message": "Tenant updated successfully"}


@router.put("/tenant/disable")
async def disable_tenant(
    tenant_id: str,
    authorize:bool=Depends(PermissionChecker(['items:write'])),
    db: AIOEngine = Depends(get_engine)
    ):
    tenant = await db.find_one(Tenant, Tenant.id == ObjectId(tenant_id))
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    if tenant.status == UserStatus.INACTIVE:
        return {"message": "User is already inactive"}

    tenant.status = UserStatus.INACTIVE
    tenant.updated_at = datetime.utcnow()
    tenant.updated_by = str(authorize.id)
    await db.save(tenant)
    return {"message": f"Tenant '{tenant.tenant_name}' disabled successfully"}


@router.get("/tenant/get-tenant")
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


@router.post("/tenant/get-all-tenants", response_model=List[Tenant])
async def list_tenants(
    filters: TenantFilterRequest,
    authorize: bool = Depends(PermissionChecker(['items:read'])),
    db: AIOEngine = Depends(get_engine),
):
    query_filter = {}

    if filters.tenant_name:
        query_filter["tenant_name"] = Regex(f".*{filters.tenant_name}.*", "i")  # case-insensitive match
    if filters.status:
        query_filter["status"] = filters.status

    tenants = [t async for t in db.find(Tenant, query_filter)]
    return tenants
