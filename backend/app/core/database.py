import ssl
from typing import Any, Dict, Tuple

from sqlalchemy import create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

# libpq-style options that hosted Postgres providers (Neon, Supabase, Render) put in their
# connection strings. pg8000 doesn't understand them, so they are turned into an SSL context.
_SSL_MODES_REQUIRING_TLS = {"require", "verify-ca", "verify-full"}
_LIBPQ_ONLY_PARAMS = {"sslmode", "channel_binding"}


def engine_options(database_url: str) -> Tuple[URL, Dict[str, Any]]:
    """Return (url, connect_args) for create_engine, normalising provider connection strings.

    Accepts the URL exactly as Neon shows it (postgresql://...?sslmode=require&channel_binding=require)
    as well as the existing postgresql+pg8000:// form.
    """
    url = make_url(database_url)

    if url.drivername.startswith("sqlite"):
        return url, {"check_same_thread": False}

    if url.drivername in ("postgres", "postgresql"):
        url = url.set(drivername="postgresql+pg8000")

    connect_args: Dict[str, Any] = {}
    if url.drivername == "postgresql+pg8000":
        sslmode = (url.query.get("sslmode") or "").lower()
        if sslmode in _SSL_MODES_REQUIRING_TLS:
            # Always verify the server certificate (stricter than libpq's "require");
            # Neon and other managed providers use publicly trusted certificates.
            connect_args["ssl_context"] = ssl.create_default_context()
        url = url.difference_update_query(_LIBPQ_ONLY_PARAMS)

    return url, connect_args


_url, _connect_args = engine_options(settings.DATABASE_URL)

engine = create_engine(
    _url,
    pool_pre_ping=True,
    # Hosted databases close idle connections; recycle before that happens
    pool_recycle=300,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
