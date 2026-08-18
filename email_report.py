from __future__ import annotations

import html
import os
import re
import smtplib
import ssl
from email.message import EmailMessage
from typing import Any

from rebalance import build_rebalance_plan, load_holdings
from reporting import build_rebalance_report_text


def send_scan_email_report(
    result: dict[str, Any],
    *,
    latest_run: dict[str, Any] | None = None,
    previous_run: dict[str, Any] | None = None,
    holdings_file: str | None = None,
) -> None:
    smtp_settings = load_smtp_settings()
    body = build_email_body(
        result,
        latest_run=latest_run,
        previous_run=previous_run,
        holdings_file=holdings_file,
    )
    html_body = build_email_html(
        result,
        latest_run=latest_run,
        previous_run=previous_run,
        holdings_file=holdings_file,
    )
    subject = build_email_subject(result)
    _send_email(
        smtp_settings=smtp_settings,
        subject=subject,
        body=body,
        html_body=html_body,
    )


def build_email_subject(result: dict[str, Any]) -> str:
    generated_at = str(result.get("generated_at") or "")
    run_status = str(result.get("run_status") or "unknown").upper()
    top_ticker = ""
    rankings = result.get("rankings", []) or []
    if rankings:
        top_ticker = str(rankings[0].get("ticker") or "")
    suffix = f" | top={top_ticker}" if top_ticker else ""
    return f"Stock Analyzer {run_status} | {generated_at}{suffix}"


def build_email_body(
    result: dict[str, Any],
    *,
    latest_run: dict[str, Any] | None = None,
    previous_run: dict[str, Any] | None = None,
    holdings_file: str | None = None,
) -> str:
    rankings = (latest_run or result).get("rankings", []) or []
    market_status = result.get("market_status", {}) or {}
    failure_error = str(result.get("failure_error") or "")
    holdings = load_holdings(holdings_file=holdings_file) if holdings_file else []
    plan = build_rebalance_plan(latest_run, previous_run, holdings) if holdings and latest_run is not None else None

    lines: list[str] = [
        "Stock Analyzer Daily Results",
        "",
        f"Generated at: {result.get('generated_at') or ''}",
        f"Run status: {result.get('run_status') or ''}",
        f"Market state: {'OPEN' if market_status.get('is_open') else 'CLOSED'}",
        f"Market reason: {market_status.get('reason') or ''}",
        f"Session date: {market_status.get('session_date') or ''}",
    ]

    if failure_error:
        lines.extend(["", f"Failure: {failure_error}", "", "No rankings were produced."])
        return "\n".join(lines)

    lines.extend(["", f"Total ranked symbols: {len(rankings)}", "", "Top rankings:"])

    if rankings:
        for row in rankings[:12]:
            metrics = row.get("metrics", {}) or {}
            lines.append(
                "  "
                + f"{row.get('rank_position', '') or '?':>2} "
                + f"{row.get('ticker') or ''} "
                + f"signal={row.get('signal') or ''} "
                + f"score={row.get('score') or ''} "
                + f"price={_format_price(row.get('price'))} "
                + f"score_change={_format_signed_number(row.get('momentum_change'))} "
                + f"1m={_format_percent(metrics.get('return_21d'))} "
                + f"3m={_format_percent(metrics.get('return_63d'))} "
                + f"rs_3m={_format_percent(metrics.get('relative_return_63d'))}"
            )
    else:
        lines.append("  (no rankings)")

    if plan is not None:
        schedule = plan.get("schedule", {}) or {}
        lines.extend(
            [
                "",
                "Monthly rebalance snapshot:",
                f"  Keep: {plan.get('summary', {}).get('keep_count', 0)}",
                f"  Sell: {plan.get('summary', {}).get('sell_count', 0)}",
                f"  Buy:  {plan.get('summary', {}).get('buy_count', 0)}",
                f"  Schedule: {schedule.get('message') or ''}",
                "",
                build_rebalance_report_text(plan),
            ]
        )

    return "\n".join(lines)


def build_email_html(
    result: dict[str, Any],
    *,
    latest_run: dict[str, Any] | None = None,
    previous_run: dict[str, Any] | None = None,
    holdings_file: str | None = None,
) -> str:
    rankings = (latest_run or result).get("rankings", []) or []
    market_status = result.get("market_status", {}) or {}
    failure_error = str(result.get("failure_error") or "")
    top_row = rankings[0] if rankings else {}
    holdings = load_holdings(holdings_file=holdings_file) if holdings_file else []
    plan = build_rebalance_plan(latest_run, previous_run, holdings) if holdings and latest_run is not None else None
    schedule = (plan or {}).get("schedule", {}) or {}
    summary = (plan or {}).get("summary", {}) or {}

    top_rows_html = "".join(_render_ranking_row_html(row) for row in rankings[:12]) or (
        "<tr><td colspan='9' style='padding:12px 14px; border-bottom:1px solid #22314c; color:#8ca0bf;'>No rankings available.</td></tr>"
    )

    sells = (plan or {}).get("current_holdings", []) or []
    buys = (plan or {}).get("buy_candidates", []) or []
    failure_html = (
        f"""
        <div style="background:#4a1111; border:1px solid #ef4444; border-radius:12px; padding:16px; margin-bottom:16px;">
          <div style="font-size:18px; font-weight:700; color:#fca5a5; margin-bottom:6px;">Scan failed</div>
          <div style="color:#fecaca; line-height:1.5;">{html.escape(failure_error)}</div>
        </div>
        """
        if failure_error
        else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en">
  <body style="margin:0; padding:0; background:#08101c; color:#e6eef9; font-family:Segoe UI, Arial, sans-serif;">
    <div style="max-width:980px; margin:0 auto; padding:24px 16px;">
      <div style="background:#10192a; border:1px solid #22314c; border-radius:16px; padding:20px; margin-bottom:16px;">
        <div style="font-size:28px; font-weight:700; margin-bottom:8px;">Stock Analyzer Daily Results</div>
        <div style="color:#8ca0bf; font-size:14px; line-height:1.6;">
          <div>Generated at: {html.escape(str(result.get("generated_at") or ""))}</div>
          <div>Run status: {html.escape(str(result.get("run_status") or ""))}</div>
          <div>Market state: {html.escape("OPEN" if market_status.get("is_open") else "CLOSED")}</div>
          <div>Market reason: {html.escape(str(market_status.get("reason") or ""))}</div>
          <div>Session date: {html.escape(str(market_status.get("session_date") or ""))}</div>
        </div>
      </div>

      {failure_html}

      <div style="margin-bottom:16px;">
        {_render_card_row_html([
            ("Top ticker", str(top_row.get("ticker") or "n/a")),
            ("Top score", _format_number(top_row.get("score")) or "n/a"),
            ("Top price", _format_price(top_row.get("price")) or "n/a"),
            ("Ranked symbols", str(len(rankings))),
        ])}
      </div>

      <div style="background:#10192a; border:1px solid #22314c; border-radius:16px; padding:0; overflow:hidden; margin-bottom:16px;">
        <div style="padding:16px 18px; border-bottom:1px solid #22314c; font-size:18px; font-weight:700;">Top momentum rankings</div>
        <table role="presentation" cellspacing="0" cellpadding="0" width="100%" style="border-collapse:collapse; width:100%;">
          <thead>
            <tr style="background:#0d1523; color:#8ca0bf; text-align:left; font-size:12px; text-transform:uppercase;">
              <th style="padding:12px 14px; border-bottom:1px solid #22314c;">Rank</th>
              <th style="padding:12px 14px; border-bottom:1px solid #22314c;">Ticker</th>
              <th style="padding:12px 14px; border-bottom:1px solid #22314c;">Signal</th>
              <th style="padding:12px 14px; border-bottom:1px solid #22314c;">Score</th>
              <th style="padding:12px 14px; border-bottom:1px solid #22314c;">Price</th>
              <th style="padding:12px 14px; border-bottom:1px solid #22314c;">Score Δ</th>
              <th style="padding:12px 14px; border-bottom:1px solid #22314c;">1M</th>
              <th style="padding:12px 14px; border-bottom:1px solid #22314c;">3M</th>
              <th style="padding:12px 14px; border-bottom:1px solid #22314c;">RS 3M</th>
            </tr>
          </thead>
          <tbody>
            {top_rows_html}
          </tbody>
        </table>
      </div>

      {(_render_rebalance_section_html(plan, schedule, summary, sells, buys) if plan is not None else "")}

      <div style="color:#8ca0bf; font-size:12px; padding:8px 2px;">
        This email is generated by the local stock analyzer scan.
      </div>
    </div>
  </body>
</html>"""


def load_smtp_settings() -> dict[str, Any]:
    smtp_host = os.environ.get("EMAIL_SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("EMAIL_SMTP_PORT", "465"))
    smtp_user = os.environ.get("EMAIL_SMTP_USER", "").strip()
    smtp_password = (
        os.environ.get("EMAIL_SMTP_APP_PASSWORD", "").strip()
        or os.environ.get("EMAIL_SMTP_PASSWORD", "").strip()
    )
    report_to = os.environ.get("REPORT_TO_EMAIL", "").strip()
    report_from = os.environ.get("REPORT_FROM_EMAIL", "").strip() or smtp_user
    recipients = _parse_recipients(report_to)

    missing = [
        name
        for name, value in [
            ("EMAIL_SMTP_USER", smtp_user),
            ("EMAIL_SMTP_APP_PASSWORD", smtp_password),
            ("REPORT_TO_EMAIL", recipients),
        ]
        if not value
    ]
    if missing:
        raise ValueError(
            "Missing email environment variables: " + ", ".join(missing)
        )

    return {
        "host": smtp_host,
        "port": smtp_port,
        "user": smtp_user,
        "password": smtp_password,
        "from": report_from,
        "to": recipients,
    }


def _send_email(*, smtp_settings: dict[str, Any], subject: str, body: str, html_body: str | None = None) -> None:
    message = EmailMessage()
    message["From"] = smtp_settings["from"]
    message["To"] = ", ".join(smtp_settings["to"])
    message["Subject"] = subject
    message.set_content(body)
    if html_body:
        message.add_alternative(html_body, subtype="html")

    context = ssl.create_default_context()
    port = int(smtp_settings["port"])
    if port == 465:
        with smtplib.SMTP_SSL(smtp_settings["host"], port, context=context, timeout=30) as server:
            server.login(smtp_settings["user"], smtp_settings["password"])
            server.send_message(message, to_addrs=smtp_settings["to"])
        return

    with smtplib.SMTP(smtp_settings["host"], port, timeout=30) as server:
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(smtp_settings["user"], smtp_settings["password"])
        server.send_message(message, to_addrs=smtp_settings["to"])


def _render_card_row_html(cards: list[tuple[str, str]]) -> str:
    card_html: list[str] = []
    for label, value in cards:
        card_html.append(
            f"""
            <div style="display:inline-block; width:calc(25% - 12px); min-width:180px; vertical-align:top; margin:0 12px 12px 0; background:#10192a; border:1px solid #22314c; border-radius:14px; padding:16px;">
              <div style="font-size:12px; text-transform:uppercase; color:#8ca0bf; margin-bottom:6px;">{html.escape(label)}</div>
              <div style="font-size:22px; font-weight:700; color:#e6eef9;">{html.escape(value)}</div>
            </div>
            """
        )
    return "".join(card_html)


def _render_ranking_row_html(row: dict[str, Any]) -> str:
    metrics = row.get("metrics", {}) or {}
    signal = str(row.get("signal") or "")
    signal_color = _signal_color(signal)
    return f"""
    <tr>
      <td style="padding:12px 14px; border-bottom:1px solid #22314c;">{html.escape(str(row.get("rank_position") or ""))}</td>
      <td style="padding:12px 14px; border-bottom:1px solid #22314c; font-weight:700;">{html.escape(str(row.get("ticker") or ""))}</td>
      <td style="padding:12px 14px; border-bottom:1px solid #22314c; color:{signal_color};">{html.escape(signal)}</td>
      <td style="padding:12px 14px; border-bottom:1px solid #22314c;">{html.escape(_format_number(row.get("score")))}</td>
      <td style="padding:12px 14px; border-bottom:1px solid #22314c;">{html.escape(_format_price(row.get("price")))}</td>
      <td style="padding:12px 14px; border-bottom:1px solid #22314c;">{html.escape(_format_signed_number(row.get("momentum_change")))}</td>
      <td style="padding:12px 14px; border-bottom:1px solid #22314c;">{html.escape(_format_percent(metrics.get("return_21d")))}</td>
      <td style="padding:12px 14px; border-bottom:1px solid #22314c;">{html.escape(_format_percent(metrics.get("return_63d")))}</td>
      <td style="padding:12px 14px; border-bottom:1px solid #22314c;">{html.escape(_format_percent(metrics.get("relative_return_63d")))}</td>
    </tr>
    """


def _render_rebalance_section_html(
    plan: dict[str, Any],
    schedule: dict[str, Any],
    summary: dict[str, Any],
    sells: list[dict[str, Any]],
    buys: list[dict[str, Any]],
) -> str:
    return f"""
      <div style="background:#10192a; border:1px solid #22314c; border-radius:16px; padding:18px; margin-bottom:16px;">
        <div style="font-size:18px; font-weight:700; margin-bottom:10px;">Rotation snapshot</div>
        <div style="color:#8ca0bf; font-size:14px; line-height:1.6; margin-bottom:14px;">
          <div>Schedule: {html.escape(str(schedule.get("message") or ""))}</div>
          <div>Keep: {html.escape(str(summary.get("keep_count", 0)))}</div>
          <div>Sell: {html.escape(str(summary.get("sell_count", 0)))}</div>
          <div>Buy: {html.escape(str(summary.get("buy_count", 0)))}</div>
          <div>QQQ/SPY fallback: {html.escape(f"{float(plan.get('fallback_allocation_pct') or 0):.1f}%")}</div>
          <div>Market regime: {html.escape(str((plan.get("market_regime") or {}).get("label") or ""))}</div>
        </div>
        {_render_action_lists_html("Current holdings actions", sells[:10], empty_message="No holdings actions available.")}
        {_render_action_lists_html("Buy candidates", buys[:10], empty_message="No buy candidates today.")}
      </div>
    """


def _render_action_lists_html(title: str, rows: list[dict[str, Any]], empty_message: str) -> str:
    if not rows:
        return f"""
        <div style="margin-top:16px;">
          <div style="font-size:15px; font-weight:700; margin-bottom:8px;">{html.escape(title)}</div>
          <div style="color:#8ca0bf; font-size:14px;">{html.escape(empty_message)}</div>
        </div>
        """

    items = []
    for row in rows:
        items.append(
            f"<li style='margin-bottom:6px;'><strong>{html.escape(str(row.get('ticker') or ''))}</strong> "
            f"- action={html.escape(str(row.get('action') or ''))}, "
            f"score={html.escape(_format_number(row.get('score')))}, "
            f"rank={html.escape(str(row.get('rank_position') or ''))}, "
            f"price={html.escape(_format_price(row.get('price')))}"
            f", destination={html.escape(str(row.get('destination') or ''))}"
            f"{_render_reason_suffix(row.get('reason'))}</li>"
        )
    return f"""
      <div style="margin-top:16px;">
        <div style="font-size:15px; font-weight:700; margin-bottom:8px;">{html.escape(title)}</div>
        <ul style="margin:0; padding-left:20px; color:#e6eef9; font-size:14px; line-height:1.5;">
          {''.join(items)}
        </ul>
      </div>
    """


def _render_reason_suffix(reason: Any) -> str:
    if not reason:
        return ""
    return f", reason={html.escape(str(reason))}"


def _parse_recipients(value: str) -> list[str]:
    return [part.strip() for part in re.split(r"[;,]", value) if part.strip()]


def _format_percent(value: Any) -> str:
    if value is None:
        return ""
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return ""


def _format_number(value: Any, decimals: int = 0) -> str:
    if value is None:
        return ""
    try:
        if decimals <= 0:
            return str(int(round(float(value))))
        return f"{float(value):.{decimals}f}"
    except (TypeError, ValueError):
        return ""


def _format_signed_number(value: Any) -> str:
    if value is None:
        return ""
    try:
        return f"{int(round(float(value))):+d}"
    except (TypeError, ValueError):
        return ""


def _signal_color(signal: str) -> str:
    mapping = {
        "STRONG_CANDIDATE": "#22c55e",
        "WATCH": "#f59e0b",
        "WATCH_FOR_ENTRY": "#f59e0b",
        "NEUTRAL": "#38bdf8",
        "WEAK": "#ef4444",
        "MOMENTUM_WEAK": "#ef4444",
    }
    return mapping.get(signal.upper(), "#e6eef9")


def _format_price(value: Any) -> str:
    if value is None:
        return ""
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return ""
