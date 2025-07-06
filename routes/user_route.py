import datetime
from operator import and_
import re
import traceback
from typing import Any, List

import bcrypt
import jwt
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Security, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, SecurityScopes
from fastapi.testclient import TestClient
from loguru import logger
from odmantic import AIOEngine
from models.schema import LoginData, PyUser, Token, UserCreate, UserFilterRequest, UserUpdate
from models.db import User, UserStatus
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
) -> Token:
    user = await authenticate_user(db,login_data.username,login_data.password)
    token_str = create_token(user)
    token = Token(access_token=token_str, token_type='bearer')
    return token

@router.post('/users/create')
async def create_user(
    user: UserCreate,
    authorize: User = Depends(PermissionChecker(['users:write'])),
    db: AIOEngine = Depends(get_engine)
):
    try:
        if not re.fullmatch(r"[A-Za-z ]+", user.name):
            raise HTTPException(status_code=400, detail="Name must contain only letters and spaces")

        # Check if username already exists (optional but safe)
        existing_user = await db.find_one(User, User.username == user.username)
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already exists")

        # Hash the password and convert bytes to str
        hashed_password = bcrypt.hashpw(user.password.encode(), bcrypt.gensalt()).decode()

        # Create User instance
        new_user = User(
            username=user.username,
            password=hashed_password,
            permissions=['items:read', 'items:write', 'users:read', 'users:write'],
            role=user.role,
            name=user.name,
            tenant_id=user.tenant_id,
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
        if not user_update.username:
            raise HTTPException(status_code=400, detail="Username is required")

        existing_user = await db.find_one(User, User.username == user_update.username)

        if not existing_user:
            raise HTTPException(status_code=404, detail="User not found")
        if not re.fullmatch(r"[A-Za-z ]+", user_update.name):
            raise HTTPException(status_code=400, detail="Name must contain only letters and spaces")


        # Update fields if provided
        if user_update.password:
            existing_user.password = bcrypt.hashpw(user_update.password.encode(), bcrypt.gensalt()).decode()
        if user_update.role is not None:
            existing_user.role = user_update.role
        if user_update.name is not None:
            existing_user.name = user_update.name
        if user_update.tenant_id is not None:
            existing_user.tenant_id = user_update.tenant_id
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
        if not username:
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


@router.post("/users/list", response_model=List[User])
async def list_users(
    filters: UserFilterRequest,
    authorize: User = Depends(PermissionChecker(["users:read"])),
    db: AIOEngine = Depends(get_engine)
):
    try:
        query_parts = []

        if filters.tenant_id:
            query_parts.append(User.tenant_id == filters.tenant_id)
        if filters.status:
            query_parts.append(User.status == filters.status)
        if filters.role:
            query_parts.append(User.role == filters.role)
        if filters.name:
            query_parts.append(User.name == filters.name)

        final_query = build_nested_and(query_parts)
        users = await db.find(User, final_query)

        return users

    except Exception as e:
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")