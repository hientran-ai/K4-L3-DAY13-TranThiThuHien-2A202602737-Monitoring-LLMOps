from __future__ import annotations

import asyncio

import httpx

from app.main import app


def test_dashboard_runtime_has_six_operational_panels() -> None:
    async def get_dashboard() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/dashboard")

    response = asyncio.run(get_dashboard())

    assert response.status_code == 200
    assert response.text.count('class="panel"') == 6
    for panel_id in ("latency", "traffic", "errors", "cost", "tokens", "quality"):
        assert f'id="{panel_id}"' in response.text
    assert "TTFT P95" in response.text
    assert "Retrieval success" in response.text
    assert "Time range: 60 minutes" in response.text
