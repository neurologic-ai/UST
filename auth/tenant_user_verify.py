from fastapi import HTTPException, status

from models.db import User, UserRole, UserStatus

def check_user_role_and_status(user: User, tenant_id: str):
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is not active"
        )

    if user.role == UserRole.ADMIN_UST:
        return True
    if user.role == UserRole.TENANT_ADMIN:
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
