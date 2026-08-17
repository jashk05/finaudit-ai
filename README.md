# FinAudit AI

A live financial reporting risk dashboard for U.S. public companies.

## What works

1. Live SEC EDGAR company ticker lookup
2. Live SEC XBRL company facts
3. Recent 10 K and 10 Q filings
4. Forensic accounting risk scoring
5. Receivables versus revenue divergence
6. Inventory versus revenue divergence
7. Cash conversion
8. Accrual intensity
9. Stock compensation intensity
10. Goodwill concentration
11. Optional Finnhub quote and company news
12. Optional OpenAI analyst explanation

## Setup

Create a virtual environment.

Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

macOS or Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies.

```bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env`.

At minimum, replace the SEC user agent email with a real contact email.

```env
SEC_USER_AGENT=FinAuditAI your-email@example.com
FINNHUB_API_KEY=
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5-mini
```

Start the app.

```bash
uvicorn app:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

## Connections

### SEC EDGAR

No API key is required for the public submissions and XBRL data APIs.

Use a descriptive `SEC_USER_AGENT` and comply with SEC fair access requirements.

### Finnhub

Add `FINNHUB_API_KEY` to enable the market snapshot and recent company news.

### OpenAI

Add `OPENAI_API_KEY` to enable the AI analyst assessment. The AI receives structured numerical results and is explicitly instructed not to treat risk signals as proof of misconduct.

## Important methodology note

The initial score is a transparent rules based risk screen. It has not yet been statistically calibrated against historical restatements or enforcement outcomes.

The next serious development step should be a point in time backtesting database. That backtest should preserve the exact filing version and information set available on each historical filing date, then evaluate subsequent restatements, Item 4.02 non reliance events, SEC accounting actions, material weaknesses and stock performance.

## Current scope

The current extractor focuses on standardized US GAAP XBRL facts from SEC filings. Company specific extension tags and qualitative accounting policy changes require a filing document extraction layer, which is the recommended second phase.

## Suggested production upgrades

1. PostgreSQL storage and caching
2. Scheduled EDGAR ingestion
3. Company specific XBRL extension handling
4. Historical point in time fact store
5. Filing text and footnote extraction
6. Industry adjusted scoring
7. Beneish M Score benchmark
8. Restatement and Item 4.02 labels
9. Authentication and saved watchlists
10. Deployment on Render, Railway, Fly.io or a cloud provider
