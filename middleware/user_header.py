from fastapi import Request
import jwt
from odmantic import AIOEngine
from db.singleton import get_engine
from models.db import User

async def add_user_headers(request: Request, call_next):
    response = await call_next(request)

    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1]
        try:
            decoded = jwt.decode(token, "secret", algorithms=["HS256"])
            username = decoded.get("sub")

            db: AIOEngine = get_engine()
            user = await db.find_one(User, User.username == username)
            if user:
                response.headers["Username-Authorities"] = user.username
                response.headers["Username-Id"] = str(user.id)
                response.headers["Role-Authorities"] = str(user.role)
        except Exception:
            # Don’t crash the whole request on header injection failure
            pass

    return response
