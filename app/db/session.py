from typing import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings
from app.core.logging import logger

# Create async engine with connection pooling
engine = create_async_engine(
    settings.async_database_uri,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an async database session per request
    and ensures proper closing / rollback on exceptions.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


async def check_db_health() -> dict:
    """
    Safely probes the PostgreSQL + PostGIS database connection.
    Executes SELECT 1, queries PostgreSQL version and PostGIS extension status.
    """
    try:
        async with engine.connect() as conn:
            # Check basic connectivity & PG version
            pg_ver_res = await conn.execute(text("SELECT version()"))
            pg_ver = pg_ver_res.scalar()

            # Check PostGIS extension
            postgis_available = False
            pgis_ver = None
            try:
                # Ensure postgis extension exists in DB
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
                postgis_version_res = await conn.execute(text("SELECT PostGIS_Version()"))
                pgis_ver = postgis_version_res.scalar()
                postgis_available = bool(pgis_ver)
            except Exception as e:
                logger.warning(f"PostGIS extension query failed: {e}")
                pgis_ver = None
                postgis_available = False

            return {
                "status": "connected",
                "database": settings.POSTGRES_DB,
                "postgres_version": pg_ver,
                "postgis_available": postgis_available,
                "postgis_version": pgis_ver,
                "detail": None,
            }
    except Exception as exc:
        return {
            "status": "disconnected",
            "database": settings.POSTGRES_DB,
            "postgres_version": None,
            "postgis_available": False,
            "postgis_version": None,
            "detail": str(exc),
        }
