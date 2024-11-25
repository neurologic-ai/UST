import uvicorn
from fastapi import FastAPI
from routes.recommendation_route import router as recommendation_router
from routes.user_route import router as user_router
from loguru import logger
from fastapi.middleware.cors import CORSMiddleware
import fastapi
from configs.manager import settings
from middleware.exception import ExceptionHandlerMiddleware
from configs.events import startup_event, shutdown_event
from fastapi.middleware.gzip import GZipMiddleware


def initialize_backend_application() -> fastapi.FastAPI:
    logger.info("Starting FastAPI application")
    app = FastAPI()
    app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=2)
    app.add_event_handler("startup", startup_event())
    app.add_event_handler("shutdown", shutdown_event())
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=settings.IS_ALLOWED_CREDENTIALS,
        allow_methods=settings.ALLOWED_METHODS,
        allow_headers=settings.ALLOWED_HEADERS,
    )
    app.add_middleware(ExceptionHandlerMiddleware)
    app.include_router(recommendation_router)
    app.include_router(user_router)
    return app


backend_app: fastapi.FastAPI = initialize_backend_application()


if __name__ == "__main__":
    uvicorn.run("main:backend_app", 
                host = settings.SERVER_HOST, 
                workers=settings.SERVER_WORKERS,
                reload=settings.SERVER_RELOAD, port = settings.SERVER_PORT,  
                log_level=settings.LOG_LEVEL)