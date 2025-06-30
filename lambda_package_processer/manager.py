import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class BackendBaseSettings(BaseSettings):
    
    MONGO_URI: str = os.environ.get("MONGO_URI")
    DB_NAME: str = os.environ.get("DB_NAME") 
    # CATEGORY_DATA_LOCATION: str = os.environ.get("CATEGORY_DATA_LOCATION") 
    api_key: str = os.environ.get("API_KEY")
    bucket_name: str = os.environ.get("BUCKET_NAME")
    aws_access_key_id: str = os.environ.get("ACCESS_KEY_ID")
    aws_secret_access_key: str = os.environ.get("SECRET_ACCESS_KEY")
    GEMINI_PROJECT: str = os.environ.get("GEMINI_PROJECT")
    GEMINI_LOCATION: str = os.environ.get("GEMINI_LOCATION")
    GEMINI_SERVICE_ACCOUNT_PATH: str = os.environ.get("GEMINI_SERVICE_ACCOUNT_PATH")
    GEMINI_API_SCOPE: str = os.environ.get("GEMINI_API_SCOPE")
    GEMINI_MODEL: str = os.environ.get("GEMINI_MODEL")
    # WEATHER_URL: str = os.environ.get("WEATHER_URL")
    # WEATHER_APIKEY: str = os.environ.get("WEATHER_APIKEY")
    # REDIS_HOST: str = os.environ.get("REDIS_HOST")
    # REDIS_PORT: int = os.environ.get("REDIS_PORT")
    
    IS_ALLOWED_CREDENTIALS: bool = True
    # get the list of allowed origins from the environment variable
    
    ALLOWED_ORIGINS: list[str]= ["http://localhost:3000"]
    ALLOWED_METHODS: list[str] = ["*"]
    ALLOWED_HEADERS: list[str] = ["*"]
    
    LOG_LEVEL:str="debug"
    model_config = SettingsConfigDict(env_file=".env")


@lru_cache
def get_settings():
    return BackendBaseSettings()

settings = get_settings()
