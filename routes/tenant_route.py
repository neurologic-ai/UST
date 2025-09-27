from datetime import datetime
import re
import secrets
from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from odmantic import AIOEngine
from bson import ObjectId
from bson.regex import Regex
from typing import List
import traceback

from auth.tenant_user_verify import check_user_role_and_status
from db.singleton import get_engine
from models.db import Location, Store, Tenant, User, UserRole, UserStatus
from models.schema import TenantCreate, TenantFilterRequest, TenantUpdate
from routes.user_route import PermissionChecker

router = APIRouter(
    prefix="/api/v2",
    tags=['tenant']
)

async def generate_unique_api_key(db: AIOEngine, max_attempts: int = 5) -> str:
    for _ in range(max_attempts):
        candidate = secrets.token_urlsafe(32)
        exists = await db.find_one(Tenant, Tenant.api_key == candidate)
        if not exists:
            return candidate
    raise RuntimeError("Failed to generate a unique API key after multiple attempts")

from pymongo.errors import DuplicateKeyError

@router.post("/tenant/create")
async def create_tenant(
    data: TenantCreate,
    authorize: User = Depends(PermissionChecker(['items:write'])),
    db: AIOEngine = Depends(get_engine)
):
    try:
        if authorize.role in {UserRole.TENANT_ADMIN, UserRole.TENANT_OP}:
                        raise HTTPException(
                status_code=401,
                detail=f"{authorize.role.value} can not do this Activity"
            )


        if not data.tenantName:
            raise HTTPException(status_code=400, detail="Tenant name is required")

        normalized_name = data.tenantName.strip().lower()

        # name must be unique
        existing_by_name = await db.find_one(Tenant, Tenant.normalized_name == normalized_name)
        if existing_by_name:
            raise HTTPException(status_code=400, detail="Tenant with this name already exists")

        # api_key must be unique (handle user-provided OR generated)
        if data.apiKey and data.apiKey.strip():
            existing_by_key = await db.find_one(Tenant, Tenant.api_key == data.apiKey.strip())
            if existing_by_key:
                raise HTTPException(status_code=400, detail="API key already in use")
            api_key = data.apiKey.strip()
        else:
            api_key = await generate_unique_api_key(db)

        tenant = Tenant(
            tenant_name=data.tenantName,
            normalized_name=normalized_name,
            api_key=api_key,
            locations=[],
            created_at=datetime.utcnow(),
            created_by=str(authorize.id),
            updated_at=None,
            updated_by=None,
            status=data.status
        )

        try:
            await db.save(tenant)
        except DuplicateKeyError as e:
            # In case a race condition slipped through
            logger.warning(f"Duplicate index violation: {e.details}")
            # Determine which unique field collided
            raise HTTPException(status_code=400, detail="Duplicate key: tenant name or api key already exists")

        return {
            "message": "Tenant created successfully",
            "id": str(tenant.id),
            "tenantName": tenant.tenant_name,
            "apiKey": api_key
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.put("/tenant/update")
async def update_tenant(
    data: TenantUpdate,
    authorize: User = Depends(PermissionChecker(['items:write'])),
    db: AIOEngine = Depends(get_engine)
):
    try:
        if not data.tenantId or not ObjectId.is_valid(data.tenantId):
            raise HTTPException(status_code=400, detail="Invalid tenant ID")

        check_user_role_and_status(authorize, data.tenantId)

        tenant = await db.find_one(Tenant, Tenant.id == ObjectId(data.tenantId))
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        updated = False

        if data.tenantName is not None:
            if not data.tenantName.strip():
                raise HTTPException(status_code=400, detail="Tenant name cannot be empty or whitespace")
            normalized_name = data.tenantName.strip().lower()

            existing = await db.find_one(
                Tenant,
                (Tenant.normalized_name == normalized_name) & (Tenant.id != tenant.id)
            )
            if existing:
                raise HTTPException(status_code=400, detail="Another tenant with this name already exists")

            tenant.tenant_name = data.tenantName
            tenant.normalized_name = normalized_name
            updated = True

        if data.apiKey is not None:
            new_key = data.apiKey.strip()
            if not new_key:
                raise HTTPException(status_code=400, detail="API key cannot be an empty string")
            # ✅ ensure unique across all tenants except self
            existing_key = await db.find_one(Tenant, (Tenant.api_key == new_key) & (Tenant.id != tenant.id))
            if existing_key:
                raise HTTPException(status_code=400, detail="API key already in use")
            tenant.api_key = new_key
            updated = True

        if data.status is not None:
            tenant.status = data.status
            updated = True

        if not updated:
            raise HTTPException(status_code=400, detail="No fields provided to update")

        tenant.updated_at = datetime.utcnow()
        tenant.updated_by = str(authorize.id)

        try:
            await db.save(tenant)
        except DuplicateKeyError as e:
            logger.warning(f"Duplicate index violation: {e.details}")
            raise HTTPException(status_code=400, detail="Duplicate key: tenant name or api key already exists")

        return {"message": "Tenant updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.put("/tenant/disable")
async def disable_tenant(
    tenantId: str,
    authorize: User = Depends(PermissionChecker(['items:write'])),
    db: AIOEngine = Depends(get_engine)
):
    try:
        if authorize.role in {UserRole.TENANT_ADMIN, UserRole.TENANT_OP}:
                        raise HTTPException(
                status_code=401,
                detail=f"{authorize.role.value} can not do this Activity"
            )
        if not tenantId or not ObjectId.is_valid(tenantId):
            raise HTTPException(status_code=400, detail="Invalid tenant ID")

        tenant = await db.find_one(Tenant, Tenant.id == ObjectId(tenantId))
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        if tenant.status == UserStatus.INACTIVE:
            return {"message": "Tenant is already inactive"}

        tenant.status = UserStatus.INACTIVE
        tenant.updated_at = datetime.utcnow()
        tenant.updated_by = str(authorize.id)
        await db.save(tenant)

        return {"message": f"Tenant '{tenant.tenant_name}' disabled successfully"}

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/tenant/get-tenant")
async def get_tenant(
    tenant_id: str,
    authorize: User = Depends(PermissionChecker(['items:read'])),
    db: AIOEngine = Depends(get_engine)
):
    try:
        if not tenant_id or not ObjectId.is_valid(tenant_id):
            raise HTTPException(status_code=400, detail="Invalid tenant ID")

        tenant = await db.find_one(Tenant, Tenant.id == ObjectId(tenant_id))
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        return tenant

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/tenant/get-all-tenants")
async def list_tenants(
    filters: TenantFilterRequest,
    authorize: User = Depends(PermissionChecker(['items:read'])),
    db: AIOEngine = Depends(get_engine),
):
    try:
        if authorize.role in {UserRole.TENANT_ADMIN, UserRole.TENANT_OP}:
                        raise HTTPException(
                status_code=401,
                detail=f"{authorize.role.value} can not do this Activity"
            )

        query_filter = {}

        if filters.tenantName:
            needle = re.escape(filters.tenantName.strip().lower())
            query_filter["normalized_name"] = Regex(f"^{needle}") 
        if filters.status:
            query_filter["status"] = filters.status

        tenants = [t async for t in db.find(Tenant, query_filter)]
        
        return {
            "totalElements": len(tenants),
            "tenants": tenants
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/tenant/regenerate-api-key")
async def regenerate_api_key(
    tenantId: str,
    authorize: User = Depends(PermissionChecker(['items:write'])),
    db: AIOEngine = Depends(get_engine)
):
    try:
        if not tenantId or not ObjectId.is_valid(tenantId):
            raise HTTPException(status_code=400, detail="Invalid tenant ID")

        check_user_role_and_status(authorize, tenantId)

        tenant = await db.find_one(Tenant, Tenant.id == ObjectId(tenantId))
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        new_api_key = await generate_unique_api_key(db)  # ✅ guaranteed unique
        tenant.api_key = new_api_key
        tenant.updated_at = datetime.utcnow()
        tenant.updated_by = str(authorize.id)

        try:
            await db.save(tenant)
        except DuplicateKeyError as e:
            logger.warning(f"Duplicate index violation: {e.details}")
            raise HTTPException(status_code=400, detail="Duplicate key: api key already exists")

        return {
            "message": "API key regenerated successfully",
            "tenantId": str(tenant.id),
            "tenantName": tenant.tenant_name,
            "apiKey": new_api_key
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
