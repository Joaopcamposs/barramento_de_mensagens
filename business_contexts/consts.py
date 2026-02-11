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

FIRST_COMPANY_ID: str = os.getenv("ID_PRIMEIRA_EMPRESA", "")
FIRST_USER_CPF: str = os.getenv("CPF_PRIMEIRO_USUARIO", "")
FIRST_USER_EMAIL: str = os.getenv("EMAIL_PRIMEIRO_USUARIO", "")
FIRST_USER_PASSWORD: str = os.getenv("SENHA_PRIMEIRO_USUARIO", "")
ADMIN_USER_PREFIX: str = os.getenv("PREFIXO_USUARIO_ADM", "")

AES_KEY = base64.b64decode(os.getenv("AES_KEY", "").encode())

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="api/token",
)
