"""Módulo de constantes e variáveis de ambiente da aplicação."""

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
FIRST_USER_EMAIL: str = os.getenv("FIRST_USER_EMAIL", "")
FIRST_USER_PASSWORD: str = os.getenv("FIRST_USER_PASSWORD", "")
ADMIN_USER_PREFIX: str = os.getenv("ADMIN_USER_PREFIX", "")

AES_KEY = base64.b64decode(os.getenv("AES_KEY", "").encode())
SECRET_KEY = os.getenv("SECRET_KEY", "")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="api/token",
)
