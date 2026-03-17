import os
from typing import List


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


_load_dotenv()

APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
IS_PRODUCTION = APP_ENV in {"production", "prod"}
DEBUG = os.getenv("DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}


def get_allowed_origins() -> List[str]:
    raw_origins = os.getenv("CORS_ORIGINS", "").strip()
    if raw_origins:
        return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
    if IS_PRODUCTION:
        return []
    return ["*"]


ALLOWED_ORIGINS = get_allowed_origins()
