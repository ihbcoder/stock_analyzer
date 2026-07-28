from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from db import get_latest_run


def build_dashboard(db_path: str | Path, output_path: str | Path) -> Path:
    latest_run = get_latest_run(db_path)
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if latest_run is None:
        latest_run = {"rankings": [], "market_status": {}, "run_status": "no_data"}

    target.write_text(_render_dashboard_html(latest_run), encoding="utf-8")
    companion_json_path = target.with_name("dashboard-data.json")
    companion_json_path.write_text(json.dumps(latest_run, indent=2), encoding="utf-8")
    return target


def _render_dashboard_html(run: dict[str, Any]) -> str:
    title_suffix = f"Run {run.get('id', 'n/a')}" if run else "No data"
    embedded_json = html.escape(json.dumps(run))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Stock Analyzer Dashboard - {html.escape(title_suffix)}</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #08101c;
      --panel: #10192a;
      --panel-2: #0d1523;
      --border: #22314c;
      --text: #e6eef9;
      --muted: #8ca0bf;
      --strong: #22c55e;
      --watch: #f59e0b;
      --neutral: #38bdf8;
      --weak: #ef4444;
      --error: #f97316;
      --accent: #7c3aed;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Segoe UI, Arial, sans-serif;
      background: linear-gradient(180deg, #0a1220 0%, #08101c 100%);
      color: var(--text);
    }}
    .wrap {{
      max-width: 1380px;
      margin: 0 auto;
      padding: 24px;
    }}
    h1, h2, h3, p {{ margin-top: 0; }}
    .topbar {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 16px;
      margin-bottom: 20px;
    }}
    .subtle {{ color: var(--muted); font-size: 14px; }}
    .status-chip {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      border: 1px solid var(--border);
      background: rgba(16, 25, 42, 0.92);
      border-radius: 999px;
      padding: 8px 12px;
      font-size: 13px;
      color: var(--muted);
    }}
    .status-dot {{
      width: 10px;
      height: 10px;
      border-radius: 999px;
      background: var(--neutral);
    }}
    .status-dot.ok {{ background: var(--strong); }}
    .status-dot.warn {{ background: var(--watch); }}
    .status-dot.err {{ background: var(--weak); }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px;
      margin-bottom: 18px;
    }}
    .card {{
      background: rgba(16, 25, 42, 0.92);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 16px;
      box-shadow: 0 8px 24px rgba(0,0,0,0.18);
    }}
    .metric-label {{
      color: var(--muted);
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    .metric-value {{
      margin-top: 8px;
      font-size: 28px;
      font-weight: 700;
    }}
    .metric-small {{
      margin-top: 8px;
      font-size: 18px;
      font-weight: 600;
    }}
    .split {{
      display: grid;
      grid-template-columns: 1.3fr 1fr;
      gap: 18px;
      margin-bottom: 18px;
    }}
    .controls {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      align-items: end;
    }}
    label {{
      display: block;
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 6px;
    }}
    input, select {{
      width: 100%;
      border: 1px solid var(--border);
      background: var(--panel-2);
      color: var(--text);
      border-radius: 10px;
      padding: 10px 12px;
      font: inherit;
    }}
    .bar-list {{
      display: grid;
      gap: 10px;
    }}
    .bar-row {{
      display: grid;
      grid-template-columns: 80px 1fr 50px;
      gap: 10px;
      align-items: center;
      font-size: 14px;
    }}
    .bar-track {{
      background: #0a1323;
      border: 1px solid var(--border);
      border-radius: 999px;
      height: 12px;
      overflow: hidden;
    }}
    .bar-fill {{
      height: 100%;
      border-radius: 999px;
    }}
    .bar-fill.STRONG {{ background: linear-gradient(90deg, #15803d, #22c55e); }}
    .bar-fill.WATCH {{ background: linear-gradient(90deg, #b45309, #f59e0b); }}
    .bar-fill.NEUTRAL {{ background: linear-gradient(90deg, #0369a1, #38bdf8); }}
    .bar-fill.WEAK {{ background: linear-gradient(90deg, #b91c1c, #ef4444); }}
    .bar-fill.ERROR {{ background: linear-gradient(90deg, #c2410c, #f97316); }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: rgba(16, 25, 42, 0.92);
      border: 1px solid var(--border);
      border-radius: 14px;
      overflow: hidden;
    }}
    th, td {{
      padding: 12px 10px;
      border-bottom: 1px solid var(--border);
      text-align: left;
      vertical-align: top;
      font-size: 14px;
    }}
    th {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      position: sticky;
      top: 0;
      background: #0f1727;
    }}
    tr:last-child td {{ border-bottom: none; }}
    .table-wrap {{
      overflow: auto;
      max-height: 900px;
      border-radius: 14px;
    }}
    .pill {{
      display: inline-block;
      padding: 4px 8px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
    }}
    .STRONG {{ background: rgba(34, 197, 94, 0.18); color: var(--strong); }}
    .WATCH {{ background: rgba(245, 158, 11, 0.18); color: var(--watch); }}
    .NEUTRAL {{ background: rgba(56, 189, 248, 0.18); color: var(--neutral); }}
    .WEAK {{ background: rgba(239, 68, 68, 0.18); color: var(--weak); }}
    .ERROR {{ background: rgba(249, 115, 22, 0.18); color: var(--error); }}
    .compact-list {{
      margin: 0;
      padding-left: 18px;
    }}
    .compact-list li {{
      margin-bottom: 4px;
    }}
    .chart-note {{
      margin-top: 8px;
      color: var(--muted);
      font-size: 13px;
    }}
    .empty {{
      color: var(--muted);
      padding: 24px 0;
    }}
    .footer {{
      margin-top: 20px;
      color: var(--muted);
      font-size: 13px;
    }}
    @media (max-width: 1000px) {{
      .split {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="topbar">
      <div>
        <h1>Stock Analyzer Dashboard</h1>
        <div class="subtle">Static dashboard generated from the latest saved run</div>
      </div>
      <div class="status-chip">
        <span id="refresh-dot" class="status-dot"></span>
        <span id="refresh-status">Auto-refresh every 60s</span>
      </div>
    </div>

    <div id="summary-grid" class="grid"></div>

    <div class="split">
      <section class="card">
        <h2>Filters</h2>
        <div class="controls">
          <div>
            <label for="search">Ticker search</label>
            <input id="search" type="text" placeholder="NVDA">
          </div>
          <div>
            <label for="signal">Signal</label>
            <select id="signal">
              <option value="">All</option>
              <option value="STRONG">STRONG</option>
              <option value="WATCH">WATCH</option>
              <option value="NEUTRAL">NEUTRAL</option>
              <option value="WEAK">WEAK</option>
              <option value="ERROR">ERROR</option>
            </select>
          </div>
          <div>
            <label for="min-score">Minimum score</label>
            <input id="min-score" type="number" min="0" max="100" value="0">
          </div>
          <div>
            <label for="sort">Sort</label>
            <select id="sort">
              <option value="rank">Saved rank</option>
              <option value="score_desc">Score descending</option>
              <option value="score_asc">Score ascending</option>
              <option value="ticker">Ticker</option>
              <option value="return_20d">20d return descending</option>
            </select>
          </div>
        </div>
      </section>

      <section class="card">
        <h2>Market status</h2>
        <div id="market-status" class="bar-list"></div>
      </section>
    </div>

    <div class="split">
      <section class="card">
        <h2>Signal distribution</h2>
        <div id="signal-chart" class="bar-list"></div>
        <div class="chart-note">Counts update as filters change.</div>
      </section>

      <section class="card">
        <h2>Top score bars</h2>
        <div id="score-chart" class="bar-list"></div>
        <div class="chart-note">Top 8 filtered symbols by score.</div>
      </section>
    </div>

    <section>
      <h2>Rankings</h2>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Rank</th>
              <th>Ticker</th>
              <th>Signal</th>
              <th>Score</th>
              <th>Price</th>
              <th>5d</th>
              <th>20d</th>
              <th>60d</th>
              <th>RSI</th>
              <th>Rel Vol</th>
              <th>Reasons</th>
              <th>Risk Flags</th>
            </tr>
          </thead>
          <tbody id="rankings-body"></tbody>
        </table>
      </div>
    </section>

    <div class="footer">
      Source file: <code>dashboard-data.json</code>
    </div>
  </div>

  <script id="dashboard-data" type="application/json">{embedded_json}</script>
  <script>
    let rawData = JSON.parse(document.getElementById("dashboard-data").textContent);
    let allRankings = Array.isArray(rawData.rankings) ? rawData.rankings.slice() : [];
    let lastLoadedAt = new Date();
    const refreshIntervalMs = 60000;

    const summaryGrid = document.getElementById("summary-grid");
    const rankingsBody = document.getElementById("rankings-body");
    const signalChart = document.getElementById("signal-chart");
    const scoreChart = document.getElementById("score-chart");
    const marketStatus = document.getElementById("market-status");
    const refreshDot = document.getElementById("refresh-dot");
    const refreshStatus = document.getElementById("refresh-status");

    const searchInput = document.getElementById("search");
    const signalSelect = document.getElementById("signal");
    const minScoreInput = document.getElementById("min-score");
    const sortSelect = document.getElementById("sort");

    function safe(value) {{
      if (value === null || value === undefined) return "";
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;");
    }}

    function percent(value) {{
      if (value === null || value === undefined || Number.isNaN(Number(value))) return "";
      return (Number(value) * 100).toFixed(1) + "%";
    }}

    function number(value, digits = 2) {{
      if (value === null || value === undefined || Number.isNaN(Number(value))) return "";
      return Number(value).toFixed(digits);
    }}

    function renderList(values) {{
      if (!values || values.length === 0) {{
        return '<span class="subtle">None</span>';
      }}
      return '<ul class="compact-list">' + values.slice(0, 4).map(item => `<li>${{safe(item)}}</li>`).join("") + "</ul>";
    }}

    function getFilteredRankings() {{
      const search = searchInput.value.trim().toUpperCase();
      const signal = signalSelect.value;
      const minScore = Number(minScoreInput.value || 0);
      const sort = sortSelect.value;

      let filtered = allRankings.filter(item => {{
        const tickerMatch = !search || String(item.ticker || "").toUpperCase().includes(search);
        const signalMatch = !signal || item.signal === signal;
        const scoreMatch = Number(item.score || 0) >= minScore;
        return tickerMatch && signalMatch && scoreMatch;
      }});

      filtered = filtered.slice();
      if (sort === "score_desc") {{
        filtered.sort((a, b) => Number(b.score || 0) - Number(a.score || 0));
      }} else if (sort === "score_asc") {{
        filtered.sort((a, b) => Number(a.score || 0) - Number(b.score || 0));
      }} else if (sort === "ticker") {{
        filtered.sort((a, b) => String(a.ticker || "").localeCompare(String(b.ticker || "")));
      }} else if (sort === "return_20d") {{
        filtered.sort((a, b) => Number(b.metrics?.return_20d || -999) - Number(a.metrics?.return_20d || -999));
      }} else {{
        filtered.sort((a, b) => Number(a.rank_position || 9999) - Number(b.rank_position || 9999));
      }}

      return filtered;
    }}

    function renderSummary(filtered) {{
      const strong = filtered.filter(item => item.signal === "STRONG").length;
      const watch = filtered.filter(item => item.signal === "WATCH").length;
      const avgScore = filtered.length
        ? (filtered.reduce((sum, item) => sum + Number(item.score || 0), 0) / filtered.length).toFixed(1)
        : "0.0";
      const best = filtered.length ? filtered[0] : null;

      const cards = [
        ["Generated at", rawData.generated_at || ""],
        ["Run status", rawData.run_status || ""],
        ["Benchmark", rawData.benchmark || ""],
        ["Filtered symbols", filtered.length],
        ["Strong candidates", strong],
        ["Watch list", watch],
        ["Average score", avgScore],
        ["Top ticker", best ? best.ticker : ""]
      ];

      summaryGrid.innerHTML = cards.map(([label, value]) => `
        <section class="card">
          <div class="metric-label">${{safe(label)}}</div>
          <div class="metric-value">${{safe(value)}}</div>
        </section>
      `).join("");
    }}

    function renderMarketStatus() {{
      const status = rawData.market_status || {{}};
      const rows = [
        ["State", status.is_open ? "OPEN" : "CLOSED"],
        ["Reason", status.reason || ""],
        ["Session date", status.session_date || ""],
        ["Opens", status.opens_at || ""],
        ["Closes", status.closes_at || ""],
        ["Next open", status.next_open_at || ""]
      ];
      marketStatus.innerHTML = rows.map(([label, value]) => `
        <div class="bar-row" style="grid-template-columns: 110px 1fr;">
          <div class="subtle">${{safe(label)}}</div>
          <div>${{safe(value)}}</div>
        </div>
      `).join("");
    }}

    function renderSignalChart(filtered) {{
      const counts = {{}};
      for (const item of filtered) {{
        const key = item.signal || "UNKNOWN";
        counts[key] = (counts[key] || 0) + 1;
      }}
      const order = ["STRONG", "WATCH", "NEUTRAL", "WEAK", "ERROR"];
      const maxCount = Math.max(1, ...order.map(key => counts[key] || 0));
      signalChart.innerHTML = order.map(key => {{
        const count = counts[key] || 0;
        const width = (count / maxCount) * 100;
        return `
          <div class="bar-row">
            <div>${{safe(key)}}</div>
            <div class="bar-track"><div class="bar-fill ${{key}}" style="width:${{width}}%"></div></div>
            <div>${{count}}</div>
          </div>
        `;
      }}).join("");
    }}

    function renderScoreChart(filtered) {{
      const top = filtered
        .slice()
        .sort((a, b) => Number(b.score || 0) - Number(a.score || 0))
        .slice(0, 8);

      if (top.length === 0) {{
        scoreChart.innerHTML = '<div class="empty">No filtered symbols.</div>';
        return;
      }}

      scoreChart.innerHTML = top.map(item => {{
        const width = Math.max(0, Math.min(100, Number(item.score || 0)));
        return `
          <div class="bar-row">
            <div>${{safe(item.ticker)}}</div>
            <div class="bar-track"><div class="bar-fill ${{safe(item.signal || "NEUTRAL")}}" style="width:${{width}}%"></div></div>
            <div>${{safe(item.score)}}</div>
          </div>
        `;
      }}).join("");
    }}

    function renderTable(filtered) {{
      if (filtered.length === 0) {{
        rankingsBody.innerHTML = `
          <tr>
            <td colspan="12" class="empty">No rows match the current filters.</td>
          </tr>
        `;
        return;
      }}

      rankingsBody.innerHTML = filtered.map(item => `
        <tr>
          <td>${{safe(item.rank_position)}}</td>
          <td>${{safe(item.ticker)}}</td>
          <td><span class="pill ${{safe(item.signal)}}">${{safe(item.signal)}}</span></td>
          <td>${{safe(item.score)}}</td>
          <td>${{number(item.price)}}</td>
          <td>${{percent(item.metrics?.return_5d)}}</td>
          <td>${{percent(item.metrics?.return_20d)}}</td>
          <td>${{percent(item.metrics?.return_60d)}}</td>
          <td>${{number(item.metrics?.rsi_14, 1)}}</td>
          <td>${{number(item.metrics?.relative_volume_20, 2)}}</td>
          <td>${{renderList(item.reasons)}}</td>
          <td>${{renderList(item.risk_flags)}}</td>
        </tr>
      `).join("");
    }}

    function renderAll() {{
      const filtered = getFilteredRankings();
      renderSummary(filtered);
      renderSignalChart(filtered);
      renderScoreChart(filtered);
      renderTable(filtered);
      renderRefreshStatus();
    }}

    function renderRefreshStatus(message = "") {{
      const generatedAt = rawData.generated_at || "unknown";
      const status = rawData.run_status || "unknown";
      const suffix = message ? ` | ${{message}}` : "";
      refreshStatus.textContent = `Auto-refresh every 60s | run=${{status}} | generated=${{generatedAt}}${{suffix}}`;
    }}

    async function refreshDashboardData() {{
      const refreshUrl = `/dashboard-data.json?t=${{Date.now()}}`;
      refreshDot.className = "status-dot warn";
      renderRefreshStatus("refreshing");

      try {{
        const response = await fetch(refreshUrl, {{
          cache: "no-store",
          headers: {{
            "cache-control": "no-cache"
          }}
        }});
        if (!response.ok) {{
          throw new Error(`HTTP ${{response.status}}`);
        }}

        const nextData = await response.json();
        rawData = nextData;
        allRankings = Array.isArray(nextData.rankings) ? nextData.rankings.slice() : [];
        lastLoadedAt = new Date();
        refreshDot.className = "status-dot ok";
        renderAll();
      }} catch (error) {{
        const secondsAgo = Math.max(0, Math.round((Date.now() - lastLoadedAt.getTime()) / 1000));
        refreshDot.className = "status-dot err";
        renderRefreshStatus(`refresh failed, last good ${{secondsAgo}}s ago`);
      }}
    }}

    renderMarketStatus();
    renderAll();
    refreshDot.className = "status-dot ok";
    setInterval(refreshDashboardData, refreshIntervalMs);

    [searchInput, signalSelect, minScoreInput, sortSelect].forEach(node => {{
      node.addEventListener("input", renderAll);
      node.addEventListener("change", renderAll);
    }});
  </script>
</body>
</html>
"""
