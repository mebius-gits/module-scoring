"""
pytest conftest：共用 fixture 定義。
"""
import pytest


@pytest.fixture
def anyio_backend():
    return "asyncio"
