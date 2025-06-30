from datetime import datetime
import bcrypt
from loguru import logger
from db.singleton import create_index, get_engine, ping,close_connection
from models.db import User, UserRole, UserStatus

def startup_event() :
    async def startup_db_client():
        try:
            logger.info("Connecting to database...")
            await ping()
            logger.info("Connected to database successfully")
            await create_index()
            
            # Create a admin user if the user collection is empty
            db = get_engine()
            admin_user = await db.find_one(User, User.username == "admin")
            if not admin_user:
                logger.info("Creating Admin user...")
                default_user = User(
                    username="admin",
                    password=bcrypt.hashpw("admin".encode(), bcrypt.gensalt()).decode(),  # decode for str
                    permissions=['items:read', 'items:write', 'users:read', 'users:write'],
                    role=UserRole.ADMIN_UST,
                    name="System Admin",
                    status=UserStatus.ACTIVE,
                    tenant_id=None,
                    created_at=datetime.utcnow(),
                    created_by=None
                )
                await db.save(default_user)
                logger.info("Admin user created successfully")
            else:
                logger.info("Admin user already exists")

        except Exception as e:
            logger.error(f"Error while starting up db : {e}")
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