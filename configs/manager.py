import decouple
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class BackendBaseSettings(BaseSettings):
    
    MONGO_URI: str = decouple.config("MONGO_URI")
    DB_NAME: str = decouple.config("DB_NAME") 
    bucket_name: str = decouple.config("BUCKET_NAME")
    aws_access_key_id: str = decouple.config("AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str = decouple.config("AWS_SECRET_ACCESS_KEY")
    GEMINI_PROJECT: str = decouple.config("GEMINI_PROJECT")
    GEMINI_LOCATION: str = decouple.config("GEMINI_LOCATION")
    GEMINI_SERVICE_ACCOUNT_PATH: str = decouple.config("GEMINI_SERVICE_ACCOUNT_PATH")
    GEMINI_API_SCOPE: str = decouple.config("GEMINI_API_SCOPE")
    GEMINI_MODEL: str = decouple.config("GEMINI_MODEL")
    WEATHER_URL: str = decouple.config("WEATHER_URL")
    WEATHER_APIKEY: str = decouple.config("WEATHER_APIKEY")
    REDIS_HOST: str = decouple.config("REDIS_HOST")
    REDIS_PORT: int = decouple.config("REDIS_PORT")
    GEOCODE_API_KEY: str = decouple.config("GEOCODE_API_KEY")
    GEOCODE_BASE_URL: str = decouple.config("GEOCODE_BASE_URL")
    ENV_NAME: str = decouple.config("ENV_NAME")
    
    IS_ALLOWED_CREDENTIALS: bool = True
    # get the list of allowed origins from the environment variable
    
    ALLOWED_ORIGINS: list[str]= ["http://localhost:3000","https://visioncheckout.fc-ust.com","http://visioncheckout.edge","http://localhost:4000"]
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
