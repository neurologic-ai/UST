import datetime
from operator import and_
import re
import traceback
from typing import Any, List
from bson.regex import Regex
import bcrypt
from bson import ObjectId
import jwt
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Security, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, SecurityScopes
from fastapi.testclient import TestClient
from loguru import logger
from odmantic import AIOEngine
from auth.tenant_user_verify import check_user_role_and_status
from models.schema import LoginData, LoginResponse, PyUser, Token, UserCreate, UserFilterRequest, UserResponse, UserUpdate
from models.db import Tenant, User, UserRole, UserStatus
from db.singleton import get_engine
from repos.user_repos import build_nested_and

router = APIRouter(
    prefix="/api/v2",
    tags=['user']
)

oauth_scheme = OAuth2PasswordBearer(
    tokenUrl="token",
    scopes={'items': 'permissions to access items'}
)



async def authenticate_user(db: AIOEngine, username: str, password: str) -> PyUser:
    exception = HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail='Invalid credentials'
                )
    user = await db.find_one(User,User.username == username)
    if user:
        if user.status != UserStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='User is disabled'
            )

        if bcrypt.checkpw(password.encode(), user.password.encode()):
            return user

    raise exception

async def get_current_user(
    db: AIOEngine = Depends(get_engine),     
    token: str = Depends(oauth_scheme)
) -> User:
    decoded = jwt.decode(token, 'secret',algorithms=['HS256'])
    username = decoded['sub']
    user = await db.find_one(User,User.username == username)
    if user:        
        return user
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Invalid credentials'
    )

class PermissionChecker:

    def __init__(self, required_permissions: list[str]) -> None:
        self.required_permissions = required_permissions

    def __call__(self, user: User = Depends(get_current_user)) -> bool:
        for r_perm in self.required_permissions:
            if r_perm not in user.permissions:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail='Permissions'
                )
        return user


def create_token(user: User) -> str:
    logger.info(user)
    payload = {'sub': user.username,
               'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=90)}
    token = jwt.encode(payload, key='secret',algorithm='HS256')
    return token

@router.post('/login')
async def login(
    login_data:  LoginData,
    db: AIOEngine = Depends(get_engine),
) -> LoginResponse:
    user = await authenticate_user(db,login_data.username,login_data.password)
    token_str = create_token(user)
    response = LoginResponse(
        access_token=token_str,
        token_type='bearer',
        role=user.role.value,
        tenantId=user.tenant_id
    )
    return response

@router.post('/users/create')
async def create_user(
    user: UserCreate,
    authorize: User = Depends(PermissionChecker(['users:write'])),
    db: AIOEngine = Depends(get_engine)
):
    try:
        tenant_id = user.tenantId.strip() if user.tenantId and user.tenantId.strip() else None
        if tenant_id:
            if not ObjectId.is_valid(tenant_id):
                raise HTTPException(status_code=400, detail="Invalid tenant ID")
            check_user_role_and_status(authorize, tenant_id)
            tenant = await db.find_one(Tenant, Tenant.id == ObjectId(tenant_id))
            if not tenant:
                raise HTTPException(status_code=400, detail="Tenant not found")
        else:
            if authorize.role in {UserRole.TENANT_ADMIN, UserRole.TENANT_OP}:
                raise HTTPException(
                    status_code=401,
                    detail="TenantId was not provided. Only UST_ADMIN can do this activity."
                )
        if not user.username.strip():
            raise HTTPException(status_code=400, detail="Username cannot be empty")

        if not user.password.strip():
            raise HTTPException(status_code=400, detail="Password cannot be empty")

        if len(user.password.strip()) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters long")

        if not re.fullmatch(r"[A-Za-z ]+", user.name):
            raise HTTPException(status_code=400, detail="Name must contain only letters and spaces")

        # Check if username already exists (optional but safe)
        existing_user = await db.find_one(User, User.username == user.username)
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already exists")
        tenant_id = user.tenantId.strip() if user.tenantId and user.tenantId.strip() else None

        if tenant_id:
            if not ObjectId.is_valid(tenant_id):
                raise HTTPException(status_code=400, detail="Invalid tenant ID")
            check_user_role_and_status(authorize, tenant_id)
            tenant = await db.find_one(Tenant, Tenant.id == ObjectId(tenant_id))
            if not tenant:
                raise HTTPException(status_code=400, detail="Tenant not found")


        # Hash the password and convert bytes to str
        hashed_password = bcrypt.hashpw(user.password.encode(), bcrypt.gensalt()).decode()

        # Create User instance
        new_user = User(
            username=user.username,
            password=hashed_password,
            permissions=['items:read', 'items:write', 'users:read', 'users:write'],
            role=user.role,
            name=user.name,
            tenant_id=tenant_id,
            created_at=datetime.datetime.utcnow(),
            created_by=str(authorize.id)
        )

        await db.save(new_user)
        return {"message": "User created successfully", "username": new_user.username}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


    


@router.get('/users/me')
def get_user(current_user: PyUser = Depends(get_current_user)):
    return current_user


@router.post('/token')
async def token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AIOEngine = Depends(get_engine),
) -> Token:
    user = await authenticate_user(db, form_data.username, form_data.password)
    token_str = create_token(user)
    return Token(access_token=token_str, token_type='bearer')



@router.put("/users/update")
async def edit_user(
    user_update: UserUpdate,
    authorize: User = Depends(PermissionChecker(["users:write"])),
    db: AIOEngine = Depends(get_engine)
):
    try:
        logger.debug(user_update.password)
        if not user_update.username:
            raise HTTPException(status_code=400, detail="Username is required")

        existing_user = await db.find_one(User, User.username == user_update.username)

        if not existing_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update fields if provided
        if user_update.password is not None:
            if not user_update.password.strip():
                raise HTTPException(status_code=400, detail="Password cannot be empty")

            if len(user_update.password.strip()) < 6:
                raise HTTPException(status_code=400, detail="Password must be at least 6 characters long")

            existing_user.password = bcrypt.hashpw(user_update.password.encode(), bcrypt.gensalt()).decode()

        if user_update.role is not None:
            existing_user.role = user_update.role
        if user_update.name is not None:
            if not re.fullmatch(r"[A-Za-z ]+", user_update.name):
                raise HTTPException(status_code=400, detail="Name must contain only letters and spaces")
            existing_user.name = user_update.name
        if user_update.tenantId is not None:  # This handles null from JSON
            tenant_id = user_update.tenantId.strip()
            if tenant_id:  # Handles empty strings like "" or "   "
                if not ObjectId.is_valid(tenant_id):
                    raise HTTPException(status_code=400, detail="Invalid tenant ID")
                check_user_role_and_status(authorize, tenant_id)
                tenant = await db.find_one(Tenant, Tenant.id == ObjectId(tenant_id))
                if not tenant:
                    raise HTTPException(status_code=400, detail="Tenant not found")

                existing_user.tenant_id = tenant_id

        if user_update.status is not None:
            existing_user.status = user_update.status

        existing_user.updated_at = datetime.datetime.utcnow()
        existing_user.updated_by = str(authorize.id)

        await db.save(existing_user)

        return {"message": "User updated successfully", "username": existing_user.username}

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.put("/users/disable")
async def disable_user(
    username: str,
    authorize: User = Depends(PermissionChecker(["users:write"])),
    db: AIOEngine = Depends(get_engine)
):
    try:
        if authorize.role == UserRole.TENANT_ADMIN:
            raise HTTPException(
                status_code=401,
                detail="Tenant admin can not do this Activity"
            )
        if not username.strip():
            raise HTTPException(status_code=400, detail="Username is required")

        user = await db.find_one(User, User.username == username)

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user.status == UserStatus.INACTIVE:
            return {"message": "User is already inactive"}

        user.status = UserStatus.INACTIVE
        user.updated_at = datetime.datetime.utcnow()
        user.updated_by = str(authorize.id)
        await db.save(user)

        return {"message": f"User '{username}' disabled successfully"}

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/users/list")
async def list_users(
    filters: UserFilterRequest,
    authorize: User = Depends(PermissionChecker(["users:read"])),
    db: AIOEngine = Depends(get_engine)
):
    try:
        query_parts = []

        if authorize.role in {UserRole.ADMIN_UST, UserRole.UST_SUPPORT}:
            if filters.tenantId:
                if not ObjectId.is_valid(filters.tenantId):
                    raise HTTPException(status_code=400, detail="Invalid tenant ID")
                tenant = await db.find_one(Tenant, Tenant.id == ObjectId(filters.tenantId))
                if not tenant:
                    raise HTTPException(status_code=404, detail="Tenant not found")
                query_parts.append(User.tenant_id == filters.tenantId)
        else:
            tenant_id = authorize.tenant_id
            logger.debug(tenant_id)
            if not ObjectId.is_valid(tenant_id):
                raise HTTPException(status_code=400, detail="Invalid tenant ID")
            tenant = await db.find_one(Tenant, Tenant.id == ObjectId(tenant_id))
            if not tenant:
                raise HTTPException(status_code=404, detail="Tenant not found")
            query_parts.append(User.tenant_id == tenant_id)
        
        if filters.id:
            if not ObjectId.is_valid(filters.id):
                raise HTTPException(status_code=400, detail="Invalid user ID")
            query_parts.append(User.id == ObjectId(filters.id))

        
        if filters.status:
            query_parts.append(User.status == filters.status)
        if filters.role:
            query_parts.append(User.role == filters.role)

        if filters.name:
            query_parts.append({"name": Regex(f".*{filters.name}.*", "i")})

        if filters.username:
            query_parts.append({"username": Regex(f".*{filters.username}.*", "i")})

        final_query = build_nested_and(query_parts)
        users = await db.find(User, final_query)

        user_responses = [
        UserResponse(
            id=str(user.id),                               
            **user.dict(exclude={'password', 'permissions', 'id'})
        )
        for user in users
    ]

        return {
            "totalElements": len(user_responses),
            "users": user_responses
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/users/{user_id}")
async def get_user(
    user_id: str,
    authorize: User = Depends(PermissionChecker(["users:read"])),
    db: AIOEngine = Depends(get_engine)
):
    try:
        if not ObjectId.is_valid(user_id):
            raise HTTPException(status_code=400, detail="Invalid user ID")

        user = await db.find_one(User, User.id == ObjectId(user_id))
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return UserResponse(
                id=str(user.id),                               
                **user.dict(exclude={'password', 'permissions', 'id'})
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
