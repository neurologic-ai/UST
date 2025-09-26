import uvicorn
from fastapi import FastAPI
from middleware.user_header import add_user_headers
from routes.recommendation_route import router as recommendation_router
from routes.user_route import router as user_router
from loguru import logger
from fastapi.middleware.cors import CORSMiddleware
import fastapi
from configs.manager import settings
from middleware.exception import ExceptionHandlerMiddleware
from configs.events import startup_event, shutdown_event
from fastapi.middleware.gzip import GZipMiddleware
from routes.tenant_route import router as tenant_router
from routes.store_route import router as store_router
from routes.fixed_alaways_reco_route import router as fixed_router


def initialize_backend_application() -> fastapi.FastAPI:
    logger.info("Starting FastAPI application")
    app = FastAPI(
        docs_url="/api/v2/docs",
        redoc_url="/api/v2/redoc",                
        openapi_url="/api/v2/openapi.json"
    )
    app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=2)
    app.add_event_handler("startup", startup_event())
    app.add_event_handler("shutdown", shutdown_event())
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],       # <-- change here
        allow_credentials=True,    # or False, depending on your need
        allow_methods=["*"],       # <-- allow all
        allow_headers=["*"],       # <-- allow all
        expose_headers=["Username-Authorities", "Role-Authorities", "Username-Id"],
    )

    app.add_middleware(ExceptionHandlerMiddleware)
    app.middleware("http")(add_user_headers)
    app.include_router(recommendation_router)
    app.include_router(user_router)
    app.include_router(tenant_router)
    app.include_router(store_router)
    app.include_router(fixed_router)
    return app


backend_app: fastapi.FastAPI = initialize_backend_application()


if __name__ == "__main__":
    uvicorn.run("main:backend_app", 
                host = settings.SERVER_HOST, 
                workers = settings.SERVER_WORKERS,
                reload = settings.SERVER_RELOAD, 
                port = settings.SERVER_PORT,  
                log_level = settings.LOG_LEVEL)