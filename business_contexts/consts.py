"""Módulo de constantes e variáveis de ambiente da aplicação."""

import os

from dotenv import load_dotenv

load_dotenv()

DB_HOST: str = os.getenv("DB_HOST", "localhost")
DB_PASSWORD: str = os.getenv("DB_PASSWORD", "password")
DB_USER: str = os.getenv("DB_USER", "postgres")
DB_NAME: str = os.getenv("DB_NAME", "postgres")
