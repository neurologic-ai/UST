from fastapi import HTTPException, Security
from fastapi.security.api_key import APIKeyQuery
from configs.manager import settings


API_KEY_NAME = "api_key"

# Define the query-based security
api_key_query = APIKeyQuery(name=API_KEY_NAME, auto_error=False)

# Dependency to validate API key
def get_api_key(api_key: str = Security(api_key_query)):
    if api_key == settings.API_KEY:
        return api_key
    else:
        raise HTTPException(
            status_code=401, detail="Invalid or missing API Key"
        )
