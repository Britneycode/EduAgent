from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(reset_database):
    """提供同步测试客户端（依赖 reset_database 确保表已创建）。"""
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
