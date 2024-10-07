import uvicorn
from fastapi import FastAPI
from routes.route import router
from loguru import logger
from fastapi.middleware.cors import CORSMiddleware
import fastapi
from configs.manager import settings
from middleware.exception import ExceptionHandlerMiddleware


def initialize_backend_application() -> fastapi.FastAPI:
    logger.info("Starting FastAPI application")
    app = FastAPI()
    logger.info(settings.ALLOWED_ORIGINS)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=settings.IS_ALLOWED_CREDENTIALS,
        allow_methods=settings.ALLOWED_METHODS,
        allow_headers=settings.ALLOWED_HEADERS,
    )
    app.add_middleware(ExceptionHandlerMiddleware)

    app.include_router(router)
    return app

backend_app: fastapi.FastAPI = initialize_backend_application()


if __name__ == "__main__":
    uvicorn.run("main:backend_app", host = "127.0.0.1", port = 8000,  log_level="info")