import os

os.environ["MONGO_URL"] = "memory://"
os.environ["DB_NAME"] = "legacy_test"
os.environ["ANTHROPIC_API_KEY"] = ""

import pytest
from httpx import ASGITransport, AsyncClient

import server
from server import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        if server.db is None:
            await server.connect_db()
        yield http
