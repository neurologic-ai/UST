import datetime
from typing import Any

import bcrypt
import jwt
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Security, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, SecurityScopes
from fastapi.testclient import TestClient
from loguru import logger
from odmantic import AIOEngine
from models.schema import LoginData, PyUser, Token, UserCreate
from models.db import User
from db.singleton import get_engine

router = APIRouter(
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
    if user and bcrypt.checkpw(password.encode(), user.password.encode()):
        return user
        
    raise exception

async def get_current_user(
    db: AIOEngine = Depends(get_engine),     
    token: str = Depends(oauth_scheme)
) -> PyUser:
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

    def __call__(self, user: PyUser = Depends(get_current_user)) -> bool:
        for r_perm in self.required_permissions:
            if r_perm not in user.permissions:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail='Permissions'
                )
        return True


def create_token(user: User) -> str:
    logger.info(user)
    payload = {'sub': user.username,
               'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=90)}
    token = jwt.encode(payload, key='secret',algorithm='HS256')
    return token

# @router.post('/token')
async def login(
    login_data:  LoginData,
    db: AIOEngine = Depends(get_engine),
) -> Token:
    user = await authenticate_user(db,login_data.username,login_data.password)
    token_str = create_token(user)
    token = Token(access_token=token_str, token_type='bearer')
    return token

# @router.post('/users/create')
async def create_user(
    user: UserCreate,
    athorize:bool=Depends(PermissionChecker(['users:write'])),
    db: AIOEngine = Depends(get_engine)
): 
    user.password = bcrypt.hashpw(user.password.encode(), bcrypt.gensalt())
    await db.save(User(**user.model_dump()))
    return user
 


# @router.get('/users/me')
def get_user(current_user: PyUser = Depends(get_current_user)):
    return current_user
