import bcrypt
from fastapi import HTTPException, status

async def authenticate_user(username: str, password: str) -> PyUser:
    exception = HTTPException(
        status_code = status.HTTP_401_UNAUTHORIZED,
        detail = 'Invalid credentials'
    )
    user = await engine.find_one(User, User.username == username)
    if not user or not bcrypt.checkpw(password.encode(), user.password.encode()):
        raise exception
    return PyUser(id=user.id, username=user.username, password = user.password, permissions = user.permissions)