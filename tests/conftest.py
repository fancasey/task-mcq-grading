import sys
from datetime import timedelta
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def mcp_session(tmp_path, anyio_backend):
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "plugin"],
        cwd=Path(__file__).resolve().parents[1],
        env={"NANOAGENT_WORKSPACE": str(tmp_path)},
    )
    async with (
        stdio_client(server) as (read, write),
        ClientSession(read, write, read_timeout_seconds=timedelta(seconds=10)) as session,
    ):
        await session.initialize()
        yield session
