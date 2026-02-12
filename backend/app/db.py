import os
from sqlalchemy import create_engine

DATABASE_URL = os.getenv("DATABASE_URL")

# Si falta, explotamos al iniciar para detectar rápido el problema
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
