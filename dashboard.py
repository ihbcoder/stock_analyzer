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
    simple_results_path = target.with_name("results.html")
    simple_results_path.write_text(_render_simple_results_html(latest_run), encoding="utf-8")
    favicon_svg_path = target.with_name("favicon.svg")
    favicon_svg_path.write_text(_render_favicon_svg(), encoding="utf-8")
    return target


def _render_dashboard_html(run: dict[str, Any]) -> str:
    title_suffix = f"Run {run.get('id', 'n/a')}" if run else "No data"
    embedded_json = json.dumps(run).replace("</", "<\\/")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Stock Analyzer Results - {html.escape(title_suffix)}</title>
  <link rel="icon" type="image/svg+xml" href="favicon.svg">
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
      max-width: 1440px;
      margin: 0 auto;
      padding: 24px;
    }}
    h1, h2, h3, p {{ margin-top: 0; }}
    .topbar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      margin-bottom: 16px;
      flex-wrap: wrap;
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
    .intro {{
      margin-bottom: 16px;
      background: rgba(16, 25, 42, 0.92);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 14px 16px;
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
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
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
    button {{
      border: 1px solid var(--border);
      background: #13213a;
      color: var(--text);
      border-radius: 10px;
      padding: 10px 14px;
      font: inherit;
      cursor: pointer;
    }}
    button:hover {{
      background: #182947;
    }}
    .results-meta {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      margin: 8px 0 14px;
      flex-wrap: wrap;
    }}
    .results-count {{
      font-size: 16px;
      font-weight: 600;
    }}
    .market-box {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 10px;
    }}
    .market-item {{
      background: #0d1523;
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 10px 12px;
    }}
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
    details {{
      min-width: 260px;
    }}
    summary {{
      cursor: pointer;
      color: var(--neutral);
      user-select: none;
    }}
    .notes {{
      margin: 8px 0 0;
      padding-left: 18px;
    }}
    .notes li {{
      margin-bottom: 4px;
    }}
    .empty {{
      color: var(--muted);
      padding: 32px 16px;
      text-align: center;
    }}
    .footer {{
      margin-top: 20px;
      color: var(--muted);
      font-size: 13px;
    }}
    @media (max-width: 900px) {{
      .results-meta {{
        align-items: flex-start;
      }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="topbar">
      <div>
        <h1>Stock Analyzer Results</h1>
        <div class="subtle">Latest saved run, sorted for review rather than charts.</div>
      </div>
      <div class="status-chip">
        <span id="refresh-dot" class="status-dot"></span>
        <span id="refresh-status">Auto-refresh every 60s</span>
      </div>
    </div>

    <section class="intro">
      <div><strong>How to use:</strong> start with no filters, sort by score, then look at the top rows. Use a minimum score like <strong>60</strong> or <strong>70</strong> to narrow the list. Use ticker search only when you want to inspect one symbol.</div>
    </section>

    <div id="summary-grid" class="grid"></div>

    <section class="card" style="margin-bottom: 18px;">
      <h2>Market status</h2>
      <div id="market-status" class="market-box"></div>
    </section>

    <section class="card" style="margin-bottom: 18px;">
      <h2>Filters</h2>
      <div class="controls">
        <div>
          <label for="search">Ticker search</label>
          <input id="search" type="text" placeholder="NVDA" autocomplete="off">
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
            <option value="score_desc">Score descending</option>
            <option value="rank">Saved rank</option>
            <option value="ticker">Ticker</option>
            <option value="return_20d">20d return descending</option>
            <option value="score_asc">Score ascending</option>
          </select>
        </div>
        <div>
          <label>&nbsp;</label>
          <button id="clear-filters" type="button">Clear filters</button>
        </div>
      </div>
    </section>

    <section>
      <div class="results-meta">
        <h2 style="margin: 0;">Rankings</h2>
        <div id="results-count" class="results-count"></div>
      </div>
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
              <th>Notes</th>
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
    const marketStatus = document.getElementById("market-status");
    const refreshDot = document.getElementById("refresh-dot");
    const refreshStatus = document.getElementById("refresh-status");
    const resultsCount = document.getElementById("results-count");

    const searchInput = document.getElementById("search");
    const signalSelect = document.getElementById("signal");
    const minScoreInput = document.getElementById("min-score");
    const sortSelect = document.getElementById("sort");
    const clearFiltersButton = document.getElementById("clear-filters");

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

    function getDefaultFilterState() {{
      return {{
        search: "",
        signal: "",
        minScore: "0",
        sort: "score_desc"
      }};
    }}

    function applyDefaultFilterState() {{
      const defaults = getDefaultFilterState();
      searchInput.value = defaults.search;
      signalSelect.value = defaults.signal;
      minScoreInput.value = defaults.minScore;
      sortSelect.value = defaults.sort;
    }}

    function renderNotes(item) {{
      const reasons = Array.isArray(item.reasons) ? item.reasons : [];
      const risks = Array.isArray(item.risk_flags) ? item.risk_flags : [];
      const hasNotes = reasons.length > 0 || risks.length > 0;
      if (!hasNotes) {{
        return '<span class="subtle">None</span>';
      }}

      const reasonItems = reasons.length
        ? `<div><strong>Reasons</strong><ul class="notes">${{reasons.slice(0, 5).map(reason => `<li>${{safe(reason)}}</li>`).join("")}}</ul></div>`
        : "";

      const riskItems = risks.length
        ? `<div style="margin-top:8px;"><strong>Risk flags</strong><ul class="notes">${{risks.slice(0, 5).map(flag => `<li>${{safe(flag)}}</li>`).join("")}}</ul></div>`
        : "";

      return `<details><summary>View notes</summary>${{reasonItems}}${{riskItems}}</details>`;
    }}

    function currentFilterSummary() {{
      const parts = [];
      if (searchInput.value.trim()) parts.push(`ticker contains "${{searchInput.value.trim().toUpperCase()}}"`);
      if (signalSelect.value) parts.push(`signal = ${{signalSelect.value}}`);
      if (Number(minScoreInput.value || 0) > 0) parts.push(`score >= ${{Number(minScoreInput.value || 0)}}`);
      return parts.length ? parts.join(", ") : "no active filters";
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
      const total = allRankings.length;
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
        ["Total symbols", total],
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
        <div class="market-item">
          <div class="subtle">${{safe(label)}}</div>
          <div style="margin-top:6px; font-weight:600;">${{safe(value)}}</div>
        </div>
      `).join("");
    }}

    function renderTable(filtered) {{
      resultsCount.textContent = `Showing ${{filtered.length}} of ${{allRankings.length}} symbols`;

      if (filtered.length === 0) {{
        rankingsBody.innerHTML = `
          <tr>
            <td colspan="11" class="empty">No rows match the current filters: ${{safe(currentFilterSummary())}}. Use "Clear filters" to reset the page.</td>
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
          <td>${{renderNotes(item)}}</td>
        </tr>
      `).join("");
    }}

    function renderAll() {{
      const filtered = getFilteredRankings();
      renderSummary(filtered);
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
      const refreshUrl = new URL("dashboard-data.json", window.location.href);
      refreshUrl.searchParams.set("t", Date.now().toString());
      refreshDot.className = "status-dot warn";
      renderRefreshStatus("refreshing");

      try {{
        const response = await fetch(refreshUrl.toString(), {{
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

    applyDefaultFilterState();
    renderMarketStatus();
    renderAll();
    refreshDot.className = "status-dot ok";
    setInterval(refreshDashboardData, refreshIntervalMs);

    [searchInput, signalSelect, minScoreInput, sortSelect].forEach(node => {{
      node.addEventListener("input", renderAll);
      node.addEventListener("change", renderAll);
    }});

    clearFiltersButton.addEventListener("click", () => {{
      applyDefaultFilterState();
      renderAll();
    }});
  </script>
</body>
</html>
"""


def _render_simple_results_html(run: dict[str, Any]) -> str:
    title_suffix = f"Run {run.get('id', 'n/a')}" if run else "No data"
    rankings = run.get("rankings", []) or []
    market_status = run.get("market_status", {}) or {}

    def fmt_percent(value: Any) -> str:
        if value is None:
            return ""
        try:
            return f"{float(value) * 100:.1f}%"
        except (TypeError, ValueError):
            return ""

    def fmt_number(value: Any, digits: int = 2) -> str:
        if value is None:
            return ""
        try:
            return f"{float(value):.{digits}f}"
        except (TypeError, ValueError):
            return ""

    def render_notes(item: dict[str, Any]) -> str:
        reasons = item.get("reasons") or []
        risk_flags = item.get("risk_flags") or []
        parts: list[str] = []
        if reasons:
            parts.append(
                "<div><strong>Reasons:</strong><ul>"
                + "".join(f"<li>{html.escape(str(reason))}</li>" for reason in reasons[:5])
                + "</ul></div>"
            )
        if risk_flags:
            parts.append(
                "<div><strong>Risk flags:</strong><ul>"
                + "".join(f"<li>{html.escape(str(flag))}</li>" for flag in risk_flags[:5])
                + "</ul></div>"
            )
        if not parts:
            return "<span class=\"muted\">None</span>"
        return "".join(parts)

    rows = []
    for item in rankings:
        metrics = item.get("metrics") or {}
        signal = html.escape(str(item.get("signal", "")))
        rows.append(
            f"""
            <tr>
              <td>{html.escape(str(item.get("rank_position", "")))}</td>
              <td>{html.escape(str(item.get("ticker", "")))}</td>
              <td><span class="pill {signal}">{signal}</span></td>
              <td>{html.escape(str(item.get("score", "")))}</td>
              <td>{fmt_number(item.get("price"))}</td>
              <td>{fmt_percent(metrics.get("return_5d"))}</td>
              <td>{fmt_percent(metrics.get("return_20d"))}</td>
              <td>{fmt_percent(metrics.get("return_60d"))}</td>
              <td>{fmt_number(metrics.get("rsi_14"), 1)}</td>
              <td>{fmt_number(metrics.get("relative_volume_20"), 2)}</td>
              <td>{render_notes(item)}</td>
            </tr>
            """
        )

    table_html = (
        """
        <tr>
          <td colspan="11" class="empty">No rankings are available in the latest saved run.</td>
        </tr>
        """
        if not rows
        else "".join(rows)
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Stock Analyzer Plain Results - {html.escape(title_suffix)}</title>
  <link rel="icon" type="image/svg+xml" href="favicon.svg">
  <style>
    :root {{
      color-scheme: dark;
      --bg: #08101c;
      --panel: #10192a;
      --border: #22314c;
      --text: #e6eef9;
      --muted: #8ca0bf;
      --strong: #22c55e;
      --watch: #f59e0b;
      --neutral: #38bdf8;
      --weak: #ef4444;
      --error: #f97316;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Segoe UI, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
    }}
    .wrap {{
      max-width: 1440px;
      margin: 0 auto;
      padding: 24px;
    }}
    .panel {{
      background: rgba(16, 25, 42, 0.95);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 16px;
      margin-bottom: 18px;
    }}
    .summary {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin-bottom: 18px;
    }}
    .metric {{
      background: rgba(16, 25, 42, 0.95);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 14px;
    }}
    .metric-label {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    .metric-value {{
      margin-top: 8px;
      font-size: 24px;
      font-weight: 700;
    }}
    .subtle, .muted {{
      color: var(--muted);
    }}
    .links {{
      margin: 12px 0 0;
      display: flex;
      gap: 16px;
      flex-wrap: wrap;
    }}
    a {{
      color: #7dd3fc;
      text-decoration: none;
    }}
    a:hover {{
      text-decoration: underline;
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
    .table-wrap {{
      overflow: auto;
      border: 1px solid var(--border);
      border-radius: 12px;
      background: rgba(16, 25, 42, 0.95);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
    }}
    th, td {{
      padding: 12px 10px;
      text-align: left;
      vertical-align: top;
      border-bottom: 1px solid var(--border);
      font-size: 14px;
    }}
    th {{
      position: sticky;
      top: 0;
      background: #0f1727;
      color: var(--muted);
      text-transform: uppercase;
      font-size: 12px;
      letter-spacing: 0.04em;
    }}
    tr:last-child td {{
      border-bottom: none;
    }}
    .empty {{
      text-align: center;
      color: var(--muted);
      padding: 32px 16px;
    }}
    ul {{
      margin: 6px 0 0;
      padding-left: 18px;
    }}
    li {{
      margin-bottom: 4px;
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="panel">
      <h1>Stock Analyzer Plain Results</h1>
      <p class="subtle">Simple static page for reviewing the latest run without interactive filters.</p>
      <div class="links">
        <a href="index.html">Open interactive page</a>
        <a href="dashboard-data.json">Open raw dashboard JSON</a>
      </div>
    </div>

    <div class="summary">
      <div class="metric">
        <div class="metric-label">Generated at</div>
        <div class="metric-value">{html.escape(str(run.get("generated_at", "")))}</div>
      </div>
      <div class="metric">
        <div class="metric-label">Run status</div>
        <div class="metric-value">{html.escape(str(run.get("run_status", "")))}</div>
      </div>
      <div class="metric">
        <div class="metric-label">Market state</div>
        <div class="metric-value">{"OPEN" if market_status.get("is_open") else "CLOSED"}</div>
      </div>
      <div class="metric">
        <div class="metric-label">Total symbols</div>
        <div class="metric-value">{len(rankings)}</div>
      </div>
      <div class="metric">
        <div class="metric-label">Top ticker</div>
        <div class="metric-value">{html.escape(str(rankings[0].get("ticker", ""))) if rankings else ""}</div>
      </div>
      <div class="metric">
        <div class="metric-label">Top score</div>
        <div class="metric-value">{html.escape(str(rankings[0].get("score", ""))) if rankings else ""}</div>
      </div>
    </div>

    <div class="panel">
      <strong>Market reason:</strong> {html.escape(str(market_status.get("reason", "")))}<br>
      <strong>Session date:</strong> {html.escape(str(market_status.get("session_date", "")))}<br>
      <strong>Opens:</strong> {html.escape(str(market_status.get("opens_at", "")))}<br>
      <strong>Closes:</strong> {html.escape(str(market_status.get("closes_at", "")))}<br>
      <strong>Next open:</strong> {html.escape(str(market_status.get("next_open_at", "")))}
    </div>

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
            <th>Notes</th>
          </tr>
        </thead>
        <tbody>
          {table_html}
        </tbody>
      </table>
    </div>
  </div>
</body>
</html>
"""


def _render_favicon_svg() -> str:
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="12" fill="#08101c"/>
  <rect x="12" y="34" width="8" height="18" rx="2" fill="#38bdf8"/>
  <rect x="28" y="24" width="8" height="28" rx="2" fill="#f59e0b"/>
  <rect x="44" y="14" width="8" height="38" rx="2" fill="#22c55e"/>
</svg>
"""
