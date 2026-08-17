import os
from datetime import date, timedelta
import httpx

class FinnhubClient:
    def __init__(self):
        self.api_key = os.getenv("FINNHUB_API_KEY", "").strip()
        self.enabled = bool(self.api_key)
        self.base = "https://finnhub.io/api/v1"

    async def _get(self, endpoint: str, params: dict):
        params = {**params, "token": self.api_key}
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(f"{self.base}{endpoint}", params=params)
            response.raise_for_status()
            return response.json()

    async def quote(self, ticker: str):
        if not self.enabled:
            return None
        data = await self._get("/quote", {"symbol": ticker})
        if not data or not data.get("c"):
            return None
        return {
            "price": data.get("c"),
            "change": data.get("d"),
            "change_pct": data.get("dp"),
            "high": data.get("h"),
            "low": data.get("l"),
            "open": data.get("o"),
            "previous_close": data.get("pc"),
            "timestamp": data.get("t"),
        }

    async def company_news(self, ticker: str):
        if not self.enabled:
            return []
        today = date.today()
        start = today - timedelta(days=14)
        data = await self._get(
            "/company-news",
            {
                "symbol": ticker,
                "from": start.isoformat(),
                "to": today.isoformat(),
            },
        )
        return [
            {
                "headline": item.get("headline"),
                "source": item.get("source"),
                "url": item.get("url"),
                "datetime": item.get("datetime"),
                "summary": item.get("summary"),
            }
            for item in data[:12]
        ]
