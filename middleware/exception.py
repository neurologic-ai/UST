
from loguru import logger
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import os

API_KEY = os.getenv("API_KEY")

class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as e:
            logger.exception(e)
            return JSONResponse(
                status_code=500, 
                content={
                    'error': e.__class__.__name__, 
                    'messages': e.args
                }
            )
        


class APIKeyQueryMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # if request.url.path in ["/docs", "/redoc", "/openapi.json"]:
        #     return await call_next(request)
        api_key = request.query_params.get("api_key")
        logger.debug(api_key)
        logger.debug(API_KEY)
        if api_key != API_KEY:
            return JSONResponse(
                status_code=401,
                content={"detail": "Unauthorized - Invalid or missing API key"}
            )
        return await call_next(request)