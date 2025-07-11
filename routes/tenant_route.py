from datetime import datetime
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

def generate_api_key() -> str:
    return secrets.token_urlsafe(32)

@router.post("/tenant/create")
async def create_tenant(
    data: TenantCreate,
    authorize: User = Depends(PermissionChecker(['items:write'])),
    db: AIOEngine = Depends(get_engine)
):
    try:
        if authorize.role == UserRole.TENANT_ADMIN:
            raise HTTPException(
                status_code=401,
                detail="Tenant admin can not do this Activity"
            )
        if not data.tenantName:
            raise HTTPException(status_code=400, detail="Tenant name is required")

        normalized_name = data.tenantName.strip().lower()
        existing = await db.find_one(Tenant, Tenant.normalized_name == normalized_name)
        if existing:
            raise HTTPException(status_code=400, detail="Tenant with this name already exists")

        api_key = data.apiKey or generate_api_key()

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

        await db.save(tenant)

        return {
            "message": "Tenant created successfully",
            "id": str(tenant.id),
            "tenantName": tenant.tenant_name,
            "apiKey": api_key
        }

    except HTTPException as e:
        raise e
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
        # Only update provided fields
        if data.tenantName is not None:
            if not data.tenantName.strip():
                raise HTTPException(status_code=400, detail="Tenant name cannot be empty or whitespace")
            normalized_name = data.tenantName.strip().lower()
            # Check for duplicate
            existing = await db.find_one(
                Tenant,
                (Tenant.normalized_name == normalized_name) & (Tenant.id != tenant.id)
            )
            if existing:
                raise HTTPException(status_code=400, detail="Another tenant with this name already exists")
            tenant.tenant_name = data.tenantName
            tenant.normalized_name = normalized_name
            updated = True

        if data.apiKey:
            if not data.apiKey.strip():
                raise HTTPException(status_code=400, detail="API key cannot be an empty string")
            tenant.api_key = data.apiKey
            updated = True

        if data.status is not None:
            tenant.status = data.status
            updated = True
        if not updated:
            raise HTTPException(status_code=400, detail="No fields provided to update")

        tenant.updated_at = datetime.utcnow()
        tenant.updated_by = str(authorize.id)

        await db.save(tenant)

        return {"message": "Tenant updated successfully"}

    except HTTPException as e:
        raise e
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
        if authorize.role == UserRole.TENANT_ADMIN:
            raise HTTPException(
                status_code=401,
                detail="Tenant admin can not do this Activity"
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


@router.post("/tenant/get-all-tenants", response_model=List[Tenant])
async def list_tenants(
    filters: TenantFilterRequest,
    authorize: User = Depends(PermissionChecker(['items:read'])),
    db: AIOEngine = Depends(get_engine)
):
    try:
        if authorize.role == UserRole.TENANT_ADMIN:
            raise HTTPException(
                status_code=401,
                detail="Tenant admin can not do this Activity"
            )
        query_filter = {}

        if filters.tenantName:
            query_filter["tenantName"] = Regex(f".*{filters.tenantName}.*", "i")
        if filters.status:
            query_filter["status"] = filters.status

        tenants = [t async for t in db.find(Tenant, query_filter)]
        return tenants
    except HTTPException as e:
        raise e
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

        new_api_key = generate_api_key()
        tenant.api_key = new_api_key
        tenant.updated_at = datetime.utcnow()
        tenant.updated_by = str(authorize.id)

        await db.save(tenant)

        return {
            "message": "API key regenerated successfully",
            "tenantId": str(tenant.id),
            "tenantName": tenant.tenant_name,
            "apiKey": new_api_key
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
