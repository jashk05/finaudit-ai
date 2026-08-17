let currentTicker = "AAPL";
let chart = null;

const el = (id) => document.getElementById(id);

function fmtPct(value, suffix = "%") {
  if (value === null || value === undefined) return "--";
  const sign = value > 0 ? "+" : "";
  return `${sign}${Number(value).toFixed(1)}${suffix}`;
}

function fmtMoney(value) {
  if (value === null || value === undefined) return "--";
  const abs = Math.abs(value);
  if (abs >= 1e12) return `$${(value / 1e12).toFixed(2)}T`;
  if (abs >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
  return `$${Number(value).toLocaleString()}`;
}

function scoreColor(score) {
  if (score >= 70) return "var(--danger)";
  if (score >= 45) return "var(--warn)";
  return "var(--accent)";
}

function setStatus(message = "", visible = true) {
  el("status").textContent = message;
  el("status").classList.toggle("hidden", !visible);
}

function renderRisk(data) {
  el("riskScore").textContent = data.risk_score;
  el("riskBand").textContent = data.risk_band;
  el("coverageValue").textContent = `${data.data_coverage}%`;
  el("coverageFill").style.width = `${data.data_coverage}%`;
  el("riskRing").style.setProperty("--score-angle", `${data.risk_score * 3.6}deg`);
  el("riskRing").style.setProperty("--accent", scoreColor(data.risk_score));
}

function renderMetrics(data) {
  const m = data.metrics;
  el("revenueGrowth").textContent = fmtPct(m.revenue_growth_pct);
  el("arDivergence").textContent = fmtPct(m.receivables_divergence_pp, " pp");
  el("cashConversion").textContent = m.cash_conversion == null ? "--" : `${m.cash_conversion.toFixed(2)}x`;
  el("sbcRatio").textContent = fmtPct(m.sbc_to_revenue_pct);
}

function renderCategories(data) {
  const entries = Object.entries(data.category_scores || {});
  el("categoryBars").innerHTML = entries.length
    ? entries.map(([name, score]) => `
      <div>
        <div class="category-row-head"><span>${name}</span><span>${score}/100</span></div>
        <div class="category-track"><div class="category-fill" style="width:${score}%; background:${scoreColor(score)}"></div></div>
      </div>
    `).join("")
    : `<div class="ai-summary">Not enough standardized data for category scoring.</div>`;
}

function renderSignals(data) {
  el("signalList").innerHTML = data.signals.map(signal => `
    <article class="signal-card" data-severity="${signal.severity}">
      <div class="signal-indicator"></div>
      <div>
        <div class="signal-title">${signal.name}</div>
        <div class="signal-detail">${signal.detail}</div>
      </div>
      <div class="signal-score">
        <strong>${signal.points} / ${signal.max_points}</strong>
        <span>${signal.category} · ${signal.severity}</span>
      </div>
    </article>
  `).join("");
}

function renderMarket(data) {
  const q = data.quote;
  const connected = data.data_sources.market !== "Not connected";
  el("marketConnection").innerHTML = `<span class="dot ${connected ? "ok" : ""}"></span> Market data`;

  if (!q) {
    el("marketPrice").textContent = connected ? "No quote" : "Not connected";
    el("marketChange").textContent = connected ? "Quote unavailable" : "Add Finnhub key for live quote";
    ["marketOpen", "marketHigh", "marketLow", "marketPrev"].forEach(id => el(id).textContent = "--");
    return;
  }

  el("marketPrice").textContent = `$${Number(q.price).toFixed(2)}`;
  const sign = q.change_pct > 0 ? "+" : "";
  el("marketChange").textContent = `${sign}${Number(q.change_pct).toFixed(2)}% · ${sign}${Number(q.change).toFixed(2)}`;
  el("marketChange").style.color = q.change_pct >= 0 ? "var(--good)" : "var(--danger)";
  el("marketOpen").textContent = `$${Number(q.open).toFixed(2)}`;
  el("marketHigh").textContent = `$${Number(q.high).toFixed(2)}`;
  el("marketLow").textContent = `$${Number(q.low).toFixed(2)}`;
  el("marketPrev").textContent = `$${Number(q.previous_close).toFixed(2)}`;
}

function renderFinancials(data) {
  const tbody = el("financialTable").querySelector("tbody");
  tbody.innerHTML = [...data.history].reverse().map(row => `
    <tr>
      <td>${row.year}</td>
      <td>${fmtMoney(row.revenue)}</td>
      <td>${fmtMoney(row.receivables)}</td>
      <td>${fmtMoney(row.inventory)}</td>
      <td>${fmtMoney(row.net_income)}</td>
      <td>${fmtMoney(row.operating_cash_flow)}</td>
      <td>${fmtMoney(row.total_assets)}</td>
      <td>${fmtMoney(row.goodwill)}</td>
      <td>${fmtMoney(row.stock_comp)}</td>
    </tr>
  `).join("");

  const ordered = [...data.history].sort((a,b) => a.year - b.year);
  const ctx = el("financialChart");
  if (chart) chart.destroy();

  chart = new Chart(ctx, {
    type: "line",
    data: {
      labels: ordered.map(x => x.year),
      datasets: [
        {
          label: "Revenue",
          data: ordered.map(x => x.revenue),
          borderColor: "#6ee7b7",
          backgroundColor: "#6ee7b7",
          tension: .28,
          pointRadius: 3
        },
        {
          label: "Operating cash flow",
          data: ordered.map(x => x.operating_cash_flow),
          borderColor: "#38bdf8",
          backgroundColor: "#38bdf8",
          tension: .28,
          pointRadius: 3
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: { labels: { color: "#9fb0b7", boxWidth: 10 } }
      },
      scales: {
        x: { ticks: { color: "#80929a" }, grid: { color: "#162730" } },
        y: {
          ticks: {
            color: "#80929a",
            callback: (v) => fmtMoney(v)
          },
          grid: { color: "#162730" }
        }
      }
    }
  });
}

function renderFilings(data) {
  el("filingsList").innerHTML = data.filings.length
    ? data.filings.map(f => {
        const accession = f.accession.replaceAll("-", "");
        const cik = String(Number(data.cik));
        const url = `https://www.sec.gov/Archives/edgar/data/${cik}/${accession}/${f.primary_document}`;
        return `
          <article class="filing-card">
            <div>
              <div class="filing-type">${f.form}</div>
              <div class="filing-date">Filed ${f.filed}${f.report_date ? ` · Report period ${f.report_date}` : ""}</div>
            </div>
            <a href="${url}" target="_blank" rel="noreferrer">Open filing ↗</a>
          </article>
        `;
      }).join("")
    : `<div class="ai-summary">No recent 10 K or 10 Q filings found.</div>`;
}

function renderNews(data) {
  const connected = data.data_sources.market !== "Not connected";
  if (!connected) {
    el("newsList").innerHTML = `<div class="ai-summary">Connect Finnhub to populate recent company news.</div>`;
    return;
  }

  el("newsList").innerHTML = data.news.length
    ? data.news.map(n => `
      <article class="news-card">
        <div>
          <div class="news-headline">${n.headline || "Untitled"}</div>
          <div class="news-source">${n.source || "Source"}</div>
          <div class="news-summary">${n.summary || ""}</div>
        </div>
        ${n.url ? `<a href="${n.url}" target="_blank" rel="noreferrer">Read ↗</a>` : ""}
      </article>
    `).join("")
    : `<div class="ai-summary">No recent company news returned.</div>`;
}

function renderConnections(data) {
  const aiConnected = data.data_sources.ai !== "Not connected";
  el("aiConnection").innerHTML = `<span class="dot ${aiConnected ? "ok" : ""}"></span> AI analysis`;
  el("aiButton").disabled = !aiConnected;
  el("aiButton").style.opacity = aiConnected ? "1" : ".45";
}

async function loadTicker(ticker) {
  ticker = ticker.trim().toUpperCase();
  if (!ticker) return;
  currentTicker = ticker;
  setStatus(`Analyzing ${ticker} using SEC filing data...`, true);
  el("analyzeButton").disabled = true;

  try {
    const response = await fetch(`/api/analyze/${encodeURIComponent(ticker)}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Analysis failed");

    el("companyTitle").textContent = `${data.company_name} (${data.ticker})`;
    el("companySubtitle").textContent =
      `Fiscal year ${data.fiscal_year} · CIK ${data.cik} · ${data.methodology_note}`;

    renderRisk(data);
    renderMetrics(data);
    renderCategories(data);
    renderSignals(data);
    renderMarket(data);
    renderFinancials(data);
    renderFilings(data);
    renderNews(data);
    renderConnections(data);

    el("aiSummary").textContent = data.data_sources.ai === "Not connected"
      ? "Connect an OpenAI API key to generate a filing aware explanation of the numerical signals."
      : "AI connection ready. Select Generate for a grounded analyst assessment.";

    setStatus("", false);
  } catch (err) {
    setStatus(err.message, true);
  } finally {
    el("analyzeButton").disabled = false;
  }
}

async function generateAI() {
  el("aiSummary").textContent = "Generating grounded analyst assessment...";
  el("aiButton").disabled = true;

  el("aiUsagePanel").classList.add("hidden");

  try {
    const response = await fetch(
      `/api/ai-summary/${encodeURIComponent(currentTicker)}`,
      { method: "POST" }
    );

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "AI analysis failed");
    }

    el("aiSummary").textContent = data.summary;

    const usage = data.usage || {};

    el("aiUsageModel").textContent =
      data.model || "Unknown";

    el("aiInputTokens").textContent =
      (usage.input_tokens ?? 0).toLocaleString();

    el("aiCachedTokens").textContent =
      (usage.cached_input_tokens ?? 0).toLocaleString();

    el("aiOutputTokens").textContent =
      (usage.output_tokens ?? 0).toLocaleString();

    el("aiTotalTokens").textContent =
      (usage.total_tokens ?? 0).toLocaleString();

    if (
      data.estimated_cost_usd !== null &&
      data.estimated_cost_usd !== undefined
    ) {
      el("aiEstimatedCost").textContent =
        `$${Number(data.estimated_cost_usd).toFixed(6)}`;
    } else {
      el("aiEstimatedCost").textContent =
        "Pricing unavailable";
    }

    el("aiUsagePanel").classList.remove("hidden");

  } catch (err) {
    el("aiSummary").textContent = err.message;
    el("aiUsagePanel").classList.add("hidden");

  } finally {
    el("aiButton").disabled = false;
  }
}

el("analyzeButton").addEventListener("click", () => loadTicker(el("tickerInput").value));
el("tickerInput").addEventListener("keydown", (event) => {
  if (event.key === "Enter") loadTicker(el("tickerInput").value);
});
el("aiButton").addEventListener("click", generateAI);

document.querySelectorAll(".navitem").forEach(button => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".navitem").forEach(x => x.classList.remove("active"));
    button.classList.add("active");
    document.getElementById(button.dataset.target).scrollIntoView({ behavior: "smooth" });
  });
});

loadTicker("AAPL");
