import base64
import os

from dotenv import load_dotenv
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext

load_dotenv()

DB_HOST: str = os.getenv("DB_HOST", "localhost")
DB_PASSWORD: str = os.getenv("DB_PASSWORD", "password")
DB_USER: str = os.getenv("DB_USER", "postgres")
DB_NAME: str = os.getenv("DB_NAME", "postgres")

FIRST_COMPANY_ID: str = os.getenv("FIRST_COMPANY_ID", "")
FIRST_USER_CPF: str = os.getenv("FIRST_USER_CPF", "")
FIRST_USER_PHONE: str = os.getenv("FIRST_USER_PHONE", "")
FIRST_USER_EMAIL: str = os.getenv("FIRST_USER_EMAIL", "")
FIRST_USER_PASSWORD: str = os.getenv("FIRST_USER_PASSWORD", "")
ADMIN_USER_PREFIX: str = os.getenv("ADMIN_USER_PREFIX", "")

AES_KEY = base64.b64decode(os.getenv("AES_KEY", "").encode())
SECRET_KEY = os.getenv("SECRET_KEY", "")
LOOKUP_HMAC_KEY = os.getenv("LOOKUP_HMAC_KEY", SECRET_KEY)
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

SENTRY_DSN = os.getenv("SENTRY_DSN", "")
TURNSTILE_SECRET_KEY = os.getenv("TURNSTILE_SECRET_KEY", "")
TURNSTILE_SITE_KEY = os.getenv("TURNSTILE_SITE_KEY", "")

_ENV_CONFIG = os.getenv("ENV_CONFIG", "").lower()
IS_LOCAL: bool = _ENV_CONFIG in ("", "local")
IN_DOCKER: bool = os.getenv("IN_DOCKER", "false").lower() == "true"
IS_TEST: bool = os.getenv("TEST_ENV", "false").lower() == "true"
IS_ALPHA: bool = _ENV_CONFIG == "alpha"
IS_PROD: bool = _ENV_CONFIG == "prod"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/token")
