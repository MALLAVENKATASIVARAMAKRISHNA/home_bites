import os
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, Request, Response, status
from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import SessionLocal
from settings import IS_PRODUCTION


def _load_secret_key() -> str:
    secret = os.getenv("SECRET_KEY", "").strip()
    if not secret:
        app_env = os.getenv("APP_ENV", "development").lower()
        if app_env in {"production", "prod"}:
            raise RuntimeError("SECRET_KEY environment variable is required in production")
        secret = secrets.token_urlsafe(48)
        os.environ["SECRET_KEY"] = secret
        print("WARNING: SECRET_KEY not set. Using an ephemeral development key.")
    if len(secret) < 32:
        raise RuntimeError("SECRET_KEY must be at least 32 characters long")
    return secret


SECRET_KEY = _load_secret_key()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
AUTH_COOKIE_NAME = "home_bites_session"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, stored_password: str) -> bool:
    try:
        if stored_password.startswith("$2"):
            return pwd_context.verify(plain_password, stored_password)
    except Exception:
        return False
    if IS_PRODUCTION:
        return False
    return plain_password == stored_password


def password_needs_rehash(stored_password: str) -> bool:
    if not stored_password.startswith("$2"):
        return True
    return pwd_context.needs_update(stored_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_token_from_request(request: Request) -> Optional[str]:
    authorization = request.headers.get("Authorization", "").strip()
    if authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()

    cookie_token = request.cookies.get(AUTH_COOKIE_NAME, "").strip()
    return cookie_token or None


def set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=IS_PRODUCTION,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(key=AUTH_COOKIE_NAME, path="/", samesite="lax")


def get_current_user(request: Request):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token = get_token_from_request(request)
    if not token:
        raise credentials_exception
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    db: Session = SessionLocal()
    try:
        user = db.execute(
            text(
                """
                SELECT user_id, name, phone_number, email, role, address, city
                FROM users
                WHERE user_id = :user_id
                """
            ),
            {"user_id": int(user_id)},
        ).mappings().first()
    finally:
        db.close()

    if user is None:
        raise credentials_exception
    return dict(user)


def get_admin_user(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
