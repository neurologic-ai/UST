import decouple
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class BackendBaseSettings(BaseSettings):
    
    MONGO_URI: str = decouple.config("MONGO_URI")
    DB_NAME: str = decouple.config("DB_NAME") 
    CATEGORY_DATA_LOCATION: str = decouple.config("CATEGORY_DATA_LOCATION") 
    api_key: str 
    bucket_name: str = decouple.config("BUCKET_NAME")
    aws_access_key_id: str = decouple.config("AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str = decouple.config("AWS_SECRET_ACCESS_KEY")
    OPENAI_API_KEY: str = decouple.config("OPENAI_API_KEY")
    
    IS_ALLOWED_CREDENTIALS: bool = True
    # get the list of allowed origins from the environment variable
    
    ALLOWED_ORIGINS: list[str]= ["http://localhost:3000"]
    ALLOWED_METHODS: list[str] = ["*"]
    ALLOWED_HEADERS: list[str] = ["*"]
    
    SERVER_HOST:str="127.0.0.1"
    SERVER_PORT:int=8000
    SERVER_WORKERS:int=4
    LOG_LEVEL:str="debug"
    SERVER_RELOAD:bool=True
    model_config = SettingsConfigDict(env_file=".env")


@lru_cache
def get_settings():
    return BackendBaseSettings()

settings = get_settings()
