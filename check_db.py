import asyncio
import asyncpg


async def test_db():
    print("Testing PostgreSQL + PostGIS connectivity...")
    try:
        conn = await asyncpg.connect(
            user="argo_user",
            password="argo_password",
            database="argo_db",
            host="localhost",
            port=5432
        )
        pg_version = await conn.fetchval("SELECT version();")
        print("PostgreSQL Version:", pg_version)
        
        # Ensure PostGIS extension
        await conn.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
        
        postgis_version = await conn.fetchval("SELECT PostGIS_Full_Version();")
        print("PostGIS Full Version:", postgis_version)
        
        extensions = await conn.fetch("SELECT extname, extversion FROM pg_extension;")
        print("Installed Extensions:", [(r["extname"], r["extversion"]) for r in extensions])
        
        await conn.close()
        print("SUCCESS: Database and PostGIS are fully accessible.")
    except Exception as exc:
        print("ERROR connecting to database:", exc)


if __name__ == "__main__":
    asyncio.run(test_db())
