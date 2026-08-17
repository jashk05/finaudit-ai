from collections import defaultdict
from math import isfinite

CONCEPTS = {
    "revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
    ],
    "receivables": [
        "AccountsReceivableNetCurrent",
        "AccountsReceivableNet",
    ],
    "inventory": [
        "InventoryNet",
    ],
    "net_income": [
        "NetIncomeLoss",
        "ProfitLoss",
    ],
    "operating_cash_flow": [
        "NetCashProvidedByUsedInOperatingActivities",
    ],
    "total_assets": [
        "Assets",
    ],
    "goodwill": [
        "Goodwill",
    ],
    "stock_comp": [
        "ShareBasedCompensation",
        "PaymentsForEmployeeBenefitsShareBasedCompensation",
    ],
}

def _finite(value):
    try:
        v = float(value)
        return v if isfinite(v) else None
    except (TypeError, ValueError):
        return None

def _growth(current, previous):
    if current is None or previous in (None, 0):
        return None
    return (current / previous) - 1

def _pct(value):
    return None if value is None else round(value * 100, 2)

def _round(value, digits=2):
    return None if value is None else round(value, digits)

def _extract_annual_series(companyfacts, concepts):
    us_gaap = companyfacts.get("facts", {}).get("us-gaap", {})

    candidates = []
    for concept in concepts:
        node = us_gaap.get(concept)
        if not node:
            continue
        units = node.get("units", {})
        usd_items = units.get("USD", [])
        for item in usd_items:
            if item.get("form") not in {"10-K", "10-K/A"}:
                continue
            if item.get("fp") != "FY":
                continue
            fy = item.get("fy")
            val = _finite(item.get("val"))
            if fy is None or val is None:
                continue
            candidates.append({
                "fy": int(fy),
                "value": val,
                "filed": item.get("filed", ""),
                "concept": concept,
                "end": item.get("end", ""),
            })

    by_year = {}
    for item in candidates:
        fy = item["fy"]
        existing = by_year.get(fy)
        if existing is None or item["filed"] > existing["filed"]:
            by_year[fy] = item

    return by_year

def _clamp(value, low=0.0, high=100.0):
    return max(low, min(high, value))

def _band(score):
    if score >= 80:
        return "Very High"
    if score >= 60:
        return "High"
    if score >= 40:
        return "Elevated"
    if score >= 20:
        return "Normal"
    return "Low"

def _severity(points, max_points):
    ratio = 0 if max_points == 0 else points / max_points
    if ratio >= 0.75:
        return "High"
    if ratio >= 0.4:
        return "Elevated"
    return "Low"

def build_analysis(ticker, company_name, cik, facts, filings):
    series = {
        metric: _extract_annual_series(facts, concepts)
        for metric, concepts in CONCEPTS.items()
    }

    common_years = sorted(
        set().union(*[set(v.keys()) for v in series.values()]),
        reverse=True,
    )
    years = common_years[:5]
    if len(years) < 2:
        raise ValueError("Not enough annual SEC XBRL history to calculate the score.")

    current_year = years[0]
    previous_year = years[1]

    def value(metric, year):
        item = series.get(metric, {}).get(year)
        return item["value"] if item else None

    current = {m: value(m, current_year) for m in CONCEPTS}
    previous = {m: value(m, previous_year) for m in CONCEPTS}

    revenue_growth = _growth(current["revenue"], previous["revenue"])
    ar_growth = _growth(current["receivables"], previous["receivables"])
    inventory_growth = _growth(current["inventory"], previous["inventory"])
    ni_growth = _growth(current["net_income"], previous["net_income"])
    ocf_growth = _growth(current["operating_cash_flow"], previous["operating_cash_flow"])

    ar_divergence = None if ar_growth is None or revenue_growth is None else ar_growth - revenue_growth
    inventory_divergence = None if inventory_growth is None or revenue_growth is None else inventory_growth - revenue_growth

    cash_conversion = None
    if current["net_income"] not in (None, 0) and current["operating_cash_flow"] is not None:
        cash_conversion = current["operating_cash_flow"] / current["net_income"]

    average_assets = None
    if current["total_assets"] is not None and previous["total_assets"] is not None:
        average_assets = (current["total_assets"] + previous["total_assets"]) / 2

    accrual_intensity = None
    if average_assets not in (None, 0) and current["net_income"] is not None and current["operating_cash_flow"] is not None:
        accrual_intensity = (current["net_income"] - current["operating_cash_flow"]) / average_assets

    sbc_ratio = None
    prev_sbc_ratio = None
    if current["stock_comp"] is not None and current["revenue"] not in (None, 0):
        sbc_ratio = current["stock_comp"] / current["revenue"]
    if previous["stock_comp"] is not None and previous["revenue"] not in (None, 0):
        prev_sbc_ratio = previous["stock_comp"] / previous["revenue"]
    sbc_ratio_change = None if sbc_ratio is None or prev_sbc_ratio is None else sbc_ratio - prev_sbc_ratio

    goodwill_ratio = None
    if current["goodwill"] is not None and current["total_assets"] not in (None, 0):
        goodwill_ratio = current["goodwill"] / current["total_assets"]
    goodwill_growth = _growth(current["goodwill"], previous["goodwill"])

    signals = []
    score = 0.0
    possible = 0.0

    def add_signal(name, category, raw, points, max_points, detail, direction="risk"):
        nonlocal score, possible
        if raw is None:
            return
        possible += max_points
        score += points
        signals.append({
            "name": name,
            "category": category,
            "severity": _severity(points, max_points),
            "points": round(points, 1),
            "max_points": max_points,
            "value": raw,
            "detail": detail,
            "direction": direction,
        })

    if ar_divergence is not None:
        pp = ar_divergence * 100
        points = _clamp((pp - 3) / 22 * 20, 0, 20)
        add_signal(
            "Receivables vs revenue",
            "Revenue quality",
            _pct(ar_divergence),
            points,
            20,
            f"Receivables grew {_pct(ar_growth)}% versus revenue growth of {_pct(revenue_growth)}%.",
        )

    if inventory_divergence is not None:
        pp = inventory_divergence * 100
        points = _clamp((pp - 4) / 26 * 12, 0, 12)
        add_signal(
            "Inventory vs revenue",
            "Working capital",
            _pct(inventory_divergence),
            points,
            12,
            f"Inventory grew {_pct(inventory_growth)}% versus revenue growth of {_pct(revenue_growth)}%.",
        )

    if cash_conversion is not None:
        points = _clamp((1.05 - cash_conversion) / 0.65 * 20, 0, 20)
        add_signal(
            "Cash conversion",
            "Earnings quality",
            _round(cash_conversion),
            points,
            20,
            f"Operating cash flow was {_round(cash_conversion)}x net income.",
        )

    if accrual_intensity is not None:
        points = _clamp((accrual_intensity - 0.01) / 0.11 * 18, 0, 18)
        add_signal(
            "Accrual intensity",
            "Earnings quality",
            _pct(accrual_intensity),
            points,
            18,
            f"Net income less operating cash flow equaled {_pct(accrual_intensity)}% of average assets.",
        )

    if sbc_ratio is not None:
        level_points = _clamp((sbc_ratio - 0.04) / 0.16 * 8, 0, 8)
        growth_points = 0
        if sbc_ratio_change is not None:
            growth_points = _clamp((sbc_ratio_change - 0.005) / 0.055 * 4, 0, 4)
        points = level_points + growth_points
        add_signal(
            "Stock compensation",
            "Non GAAP pressure",
            _pct(sbc_ratio),
            points,
            12,
            f"Stock compensation was {_pct(sbc_ratio)}% of revenue"
            + (f", changing {_pct(sbc_ratio_change)} percentage points year over year." if sbc_ratio_change is not None else "."),
        )

    if goodwill_ratio is not None:
        growth_component = 0
        if goodwill_growth is not None:
            growth_component = _clamp((goodwill_growth - 0.10) / 0.70 * 4, 0, 4)
        level_component = _clamp((goodwill_ratio - 0.15) / 0.45 * 4, 0, 4)
        points = growth_component + level_component
        add_signal(
            "Goodwill concentration",
            "Balance sheet",
            _pct(goodwill_ratio),
            points,
            8,
            f"Goodwill represented {_pct(goodwill_ratio)}% of total assets"
            + (f" and changed {_pct(goodwill_growth)}% year over year." if goodwill_growth is not None else "."),
        )

    normalized_score = 0 if possible == 0 else round(score / possible * 100)
    coverage = round(possible / 90 * 100)
    normalized_score = round(normalized_score * (0.85 + 0.15 * min(1, possible / 90)))

    category_points = defaultdict(float)
    category_possible = defaultdict(float)
    for signal in signals:
        category_points[signal["category"]] += signal["points"]
        category_possible[signal["category"]] += signal["max_points"]

    category_scores = {
        category: round(category_points[category] / category_possible[category] * 100)
        for category in category_points
        if category_possible[category]
    }

    history = []
    for year in sorted(years):
        row = {"year": year}
        for metric in CONCEPTS:
            row[metric] = value(metric, year)
        history.append(row)

    recent_financial_filings = [
        filing for filing in filings if filing["form"].startswith(("10-K", "10-Q"))
    ][:10]

    latest_filing = recent_financial_filings[0] if recent_financial_filings else None

    return {
        "ticker": ticker,
        "company_name": company_name,
        "cik": cik,
        "fiscal_year": current_year,
        "risk_score": normalized_score,
        "risk_band": _band(normalized_score),
        "data_coverage": min(100, coverage),
        "metrics": {
            "revenue_growth_pct": _pct(revenue_growth),
            "receivables_growth_pct": _pct(ar_growth),
            "receivables_divergence_pp": _pct(ar_divergence),
            "inventory_growth_pct": _pct(inventory_growth),
            "inventory_divergence_pp": _pct(inventory_divergence),
            "net_income_growth_pct": _pct(ni_growth),
            "ocf_growth_pct": _pct(ocf_growth),
            "cash_conversion": _round(cash_conversion),
            "accrual_intensity_pct": _pct(accrual_intensity),
            "sbc_to_revenue_pct": _pct(sbc_ratio),
            "sbc_ratio_change_pp": _pct(sbc_ratio_change),
            "goodwill_to_assets_pct": _pct(goodwill_ratio),
            "goodwill_growth_pct": _pct(goodwill_growth),
        },
        "category_scores": category_scores,
        "signals": sorted(signals, key=lambda x: x["points"] / x["max_points"], reverse=True),
        "history": history,
        "filings": recent_financial_filings,
        "latest_filing": latest_filing,
        "methodology_note": (
            "This is a financial reporting risk screen, not a fraud determination. "
            "Signals require investigation and can have legitimate business explanations."
        ),
    }
