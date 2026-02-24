# app/db.py

import os
from sqlalchemy import create_engine


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, "").strip() or default)
    except Exception:
        return default


DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

# Si falta, explotamos al iniciar para detectar rápido el problema
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

# Pool settings (ajustables por env)
DB_POOL_SIZE = _env_int("DB_POOL_SIZE", 10)          # conexiones “base”
DB_MAX_OVERFLOW = _env_int("DB_MAX_OVERFLOW", 20)    # extras en pico
DB_POOL_TIMEOUT = _env_int("DB_POOL_TIMEOUT", 30)    # segundos esperando conexión libre
DB_POOL_RECYCLE = _env_int("DB_POOL_RECYCLE", 1800)  # recicla cada 30 min (evita conexiones zombies)

# Driver timeouts (PostgreSQL)
# Nota: connect_timeout es estándar; keepalives ayuda en redes “caprichosas”.
connect_args = {
    "connect_timeout": _env_int("DB_CONNECT_TIMEOUT", 10),
    "keepalives": 1,
    "keepalives_idle": _env_int("DB_KEEPALIVES_IDLE", 30),
    "keepalives_interval": _env_int("DB_KEEPALIVES_INTERVAL", 10),
    "keepalives_count": _env_int("DB_KEEPALIVES_COUNT", 5),
}

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_timeout=DB_POOL_TIMEOUT,
    pool_recycle=DB_POOL_RECYCLE,
    connect_args=connect_args,
)