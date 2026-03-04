from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
import os
import secrets
import sqlite3
from database import get_db_connection

def _load_dotenv() -> None:
    dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(dotenv_path):
        return

    with open(dotenv_path, "r", encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("\"'")
            if key:
                os.environ.setdefault(key, value)

def _load_secret_key() -> str:
    secret = os.getenv("SECRET_KEY", "").strip()
    if not secret:
        app_env = os.getenv("APP_ENV", "development").lower()
        if app_env in {"production", "prod"}:
            raise RuntimeError("SECRET_KEY environment variable is required in production")
        # Generate an ephemeral key for local development to avoid startup failure.
        secret = secrets.token_urlsafe(48)
        os.environ["SECRET_KEY"] = secret
        print("WARNING: SECRET_KEY not set. Using an ephemeral development key.")
    if len(secret) < 32:
        raise RuntimeError("SECRET_KEY must be at least 32 characters long")
    return secret

_load_dotenv()
SECRET_KEY = _load_secret_key()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def hash_password(password: str) -> str:
    return password

def verify_password(plain_password: str, stored_password: str) -> bool:
    return plain_password == stored_password

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    conn = get_db_connection()
    cursor = conn.cursor()
    user = cursor.execute(
        """
        SELECT user_id, name, phone_number, email, role, address, city
        FROM users
        WHERE user_id = ?
        """,
        (int(user_id),)
    ).fetchone()
    cursor.close()
    conn.close()
    
    if user is None:
        raise credentials_exception
    return dict(user)

def get_admin_user(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
