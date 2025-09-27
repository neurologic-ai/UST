from typing import List, Optional
from bson import ObjectId
from fastapi import HTTPException, status
from odmantic import AIOEngine

from models.db import Tenant, User, UserRole, UserStatus

def check_user_role_and_status(user: User, tenant_id: str):
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is not active"
        )

    if user.role in {UserRole.ADMIN_UST, UserRole.UST_SUPPORT}:
        return True
    if user.role in {UserRole.TENANT_ADMIN, UserRole.TENANT_OP}:
        if user.tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tenant admin does not belong to this tenant"
            )
        return True
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="User does not have required role"
    )



async def resolve_tenants_for_read(
    db: AIOEngine, authorize: User, tenant_id_opt: Optional[str]
) -> List[Tenant]:
    # Global roles can read across tenants
    if authorize.role in {UserRole.ADMIN_UST, UserRole.UST_SUPPORT}:
        if tenant_id_opt:
            if not ObjectId.is_valid(tenant_id_opt):
                raise HTTPException(status_code=400, detail="Invalid tenant ID")
            tenant = await db.find_one(Tenant, Tenant.id == ObjectId(tenant_id_opt))
            if not tenant:
                raise HTTPException(status_code=404, detail="Tenant not found")
            return [tenant]
        return [t async for t in db.find(Tenant, {})]

    # Tenant-scoped roles → must belong to their own tenant
    tenant_id = tenant_id_opt or authorize.tenant_id
    if not tenant_id or not ObjectId.is_valid(tenant_id):
        raise HTTPException(status_code=400, detail="Invalid tenant ID")

    check_user_role_and_status(authorize, tenant_id)

    tenant = await db.find_one(Tenant, Tenant.id == ObjectId(tenant_id))
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return [tenant]
