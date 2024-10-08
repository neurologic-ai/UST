

from loguru import logger
from db.singleton import ping,close_connection


def startup_event() :
    async def startup_db_client():
        try:
            logger.info("Connecting to database...")
            await ping()
            
            logger.info("Connected to database successfully")
        except Exception as e:
            logger.error(f"Error in connecting to database: {e}")
    return startup_db_client

def shutdown_event():
    async def shutdown_db_client():
        try:
            logger.info("Closing database connection...")
            await close_connection()
            logger.info("Database connection closed successfully")
        except Exception as e:
            logger.error(f"Error in closing database connection: {e}")
        return shutdown_db_client