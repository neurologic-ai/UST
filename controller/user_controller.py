# import datetime
# from typing import Any

import bcrypt
from fastapi import HTTPException, status
# from fastapi.security import OAuth2PasswordBearer
# from odmantic import AIOEngine, Model
# from motor.motor_asyncio import AsyncIOMotorClient
# from pydantic import BaseModel

async def authenticate_user(username: str, password: str) -> PyUser:
    exception = HTTPException(
        status_code = status.HTTP_401_UNAUTHORIZED,
        detail = 'Invalid credentials'
    )
    user = await engine.find_one(User, User.username == username)
    if not user or not bcrypt.checkpw(password.encode(), user.password.encode()):
        raise exception
    return PyUser(id=user.id, username=user.username, password = user.password, permissions = user.permissions)