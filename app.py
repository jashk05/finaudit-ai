from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv


# Load environment variables before importing services
load_dotenv()


from services.sec import SecClient
from services.finnhub import FinnhubClient
from services.scoring import build_analysis
from services.ai import summarize_analysis


BASE_DIR = Path(__file__).resolve().parent


app = FastAPI(
    title="FinAudit AI",
    version="0.1.0"
)


sec = SecClient()
market = FinnhubClient()


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "sec": True,
        "finnhub": market.enabled,
        "ai": summarize_analysis.enabled,
    }


@app.get("/api/analyze/{ticker}")
async def analyze(ticker: str):
    ticker = ticker.upper().strip()

    try:
        company = await sec.company_overview(ticker)

        facts = await sec.company_facts(
            company["cik"]
        )

        filings = await sec.recent_filings(
            company["cik"]
        )

        analysis = build_analysis(
            ticker=ticker,
            company_name=company["name"],
            cik=company["cik"],
            facts=facts,
            filings=filings,
        )

        quote = (
            await market.quote(ticker)
            if market.enabled
            else None
        )

        news = (
            await market.company_news(ticker)
            if market.enabled
            else []
        )

        analysis["quote"] = quote
        analysis["news"] = news[:8]

        analysis["data_sources"] = {
            "financials": "SEC EDGAR XBRL",
            "market": (
                "Finnhub"
                if market.enabled
                else "Not connected"
            ),
            "ai": (
                "Google Gemini"
                if summarize_analysis.enabled
                else "Not connected"
            ),
        }

        return analysis

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc)
        )

    except Exception as exc:
        import traceback

        print("\n=== ANALYSIS ERROR ===")
        print(f"Error type: {type(exc).__name__}")
        print(f"Error message: {exc}")
        traceback.print_exc()
        print("=== END ANALYSIS ERROR ===\n")

        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {exc}"
        )


@app.post("/api/ai-summary/{ticker}")
async def ai_summary(ticker: str):
    ticker = ticker.upper().strip()

    if not summarize_analysis.enabled:
        raise HTTPException(
            status_code=503,
            detail="AI API key is not configured."
        )

    try:
        company = await sec.company_overview(ticker)

        facts = await sec.company_facts(
            company["cik"]
        )

        filings = await sec.recent_filings(
            company["cik"]
        )

        analysis = build_analysis(
            ticker=ticker,
            company_name=company["name"],
            cik=company["cik"],
            facts=facts,
            filings=filings,
        )

        result = await summarize_analysis(
            analysis
        )

        if result is None:
            raise RuntimeError(
                "AI analysis returned no result."
            )

        return result

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc)
        )

    except Exception as exc:
        import traceback

        print("\n=== AI SUMMARY ERROR ===")
        print(f"Error type: {type(exc).__name__}")
        print(f"Error message: {exc}")

        traceback.print_exc()

        print("=== END AI SUMMARY ERROR ===\n")

        raise HTTPException(
            status_code=500,
            detail=f"AI summary failed: {exc}"
        )


app.mount(
    "/static",
    StaticFiles(
        directory=BASE_DIR / "static"
    ),
    name="static"
)


@app.get("/")
async def home():
    return FileResponse(
        BASE_DIR
        / "static"
        / "index.html"
    )