import os
from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyQuery, APIKey
from fastapi.routing import APIRouter
from odmantic import AIOEngine
from configs.manager import settings
from db.singleton import get_engine
from models.db import Tenant

# API_KEY = settings.api_key
API_KEY_NAME = "api_key"

# Define the query-based security
api_key_query = APIKeyQuery(name=API_KEY_NAME, auto_error=False)

# # Dependency to validate API key
# def get_api_key(api_key: str = Security(api_key_query)):
#     if api_key == API_KEY:
#         return api_key
#     else:
#         raise HTTPException(
#             status_code=401, detail="Invalid or missing API Key"
#         )

async def get_current_tenant(
    api_key: str = Security(api_key_query),
    db: AIOEngine = Depends(get_engine)
) -> Tenant:
    tenant = await db.find_one(Tenant, Tenant.api_key == api_key)
    if not tenant:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return tenant