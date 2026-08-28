import asyncio
import json
from httpx import ASGITransport, AsyncClient
from app.main import app


async def run_live_probe():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://localhost:8000") as client:
        response = await client.get("/health")
        print("HTTP Status:", response.status_code)
        print("Response JSON:")
        print(json.dumps(response.json(), indent=2))


if __name__ == "__main__":
    asyncio.run(run_live_probe())
