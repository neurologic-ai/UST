import datetime
from typing import Any

import bcrypt
import jwt
from fastapi import Depends, FastAPI, HTTPException, Security, status
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from fastapi.testclient import TestClient

def authenticate_user(username: str, password: str) -> PyUser:
    exception = HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail='Invalid credentials'
                )
    
    raise exception