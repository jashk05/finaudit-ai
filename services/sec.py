import os
import time
import httpx

SEC_DATA = "https://data.sec.gov"
SEC_WWW = "https://www.sec.gov"

class SecClient:
    def __init__(self):
        self.user_agent = os.getenv(
            "SEC_USER_AGENT",
            "FinAuditAI research-dashboard contact@example.com"
        )
        self.headers = {
            "User-Agent": self.user_agent,
            "Accept-Encoding": "gzip, deflate",
            "Host": "data.sec.gov",
        }
        self._ticker_cache = None
        self._ticker_cache_time = 0

    async def _get_json(self, url: str, host: str = "data.sec.gov"):
        headers = dict(self.headers)
        headers["Host"] = host
        async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()

    async def ticker_map(self):
        if self._ticker_cache and time.time() - self._ticker_cache_time < 86400:
            return self._ticker_cache

        data = await self._get_json(
            f"{SEC_WWW}/files/company_tickers.json",
            host="www.sec.gov"
        )

        mapped = {}
        for item in data.values():
            mapped[item["ticker"].upper()] = {
                "cik": str(item["cik_str"]).zfill(10),
                "name": item["title"],
            }

        self._ticker_cache = mapped
        self._ticker_cache_time = time.time()
        return mapped

    async def company_overview(self, ticker: str):
        companies = await self.ticker_map()
        if ticker not in companies:
            raise ValueError(f"Ticker {ticker} was not found in the SEC ticker map.")
        return companies[ticker]

    async def company_facts(self, cik: str):
        return await self._get_json(
            f"{SEC_DATA}/api/xbrl/companyfacts/CIK{cik}.json"
        )

    async def recent_filings(self, cik: str):
        submissions = await self._get_json(
            f"{SEC_DATA}/submissions/CIK{cik}.json"
        )
        recent = submissions.get("filings", {}).get("recent", {})

        output = []
        count = len(recent.get("accessionNumber", []))
        for idx in range(min(count, 80)):
            form = recent.get("form", [""] * count)[idx]
            if form not in {"10-K", "10-K/A", "10-Q", "10-Q/A", "8-K", "8-K/A"}:
                continue
            output.append({
                "form": form,
                "filed": recent.get("filingDate", [""] * count)[idx],
                "report_date": recent.get("reportDate", [""] * count)[idx],
                "accession": recent.get("accessionNumber", [""] * count)[idx],
                "primary_document": recent.get("primaryDocument", [""] * count)[idx],
            })
        return output
