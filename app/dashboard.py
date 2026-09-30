from __future__ import annotations

import html
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml


LOG_PATH = Path(os.getenv("LOG_PATH", "data/logs.jsonl"))
CONFIG_PATH = Path("config/dashboard.yaml")
CHALLENGE_PATH = Path("config/challenge.json")


def _timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _load_records(path: Path = LOG_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = _timestamp(record.get("ts"))
        if ts is not None:
            record["_ts"] = ts
            records.append(record)
    return sorted(records, key=lambda record: record["_ts"])


def _percentile(values: list[float], p: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round((p / 100) * len(ordered) + 0.5) - 1))
    return ordered[index]


def _number(record: dict[str, Any], key: str) -> float:
    value = record.get(key, 0)
    return float(value) if isinstance(value, (int, float)) else 0.0


def _minute(ts: datetime) -> datetime:
    return ts.replace(second=0, microsecond=0)


def _series_svg(
    series: list[tuple[str, list[tuple[datetime, float]], str]],
    *,
    threshold: float | None = None,
) -> str:
    points = [point for _, values, _ in series for point in values]
    if not points:
        return '<div class="empty">No data in this window</div>'

    times = [point[0].timestamp() for point in points]
    values = [point[1] for point in points]
    if threshold is not None:
        values.append(threshold)
    min_time, max_time = min(times), max(times)
    max_value = max(max(values), 1.0)
    width, height, chart_pad = 620, 170, 24

    def x_coord(ts: datetime) -> float:
        span = max(max_time - min_time, 1.0)
        return chart_pad + (ts.timestamp() - min_time) / span * (width - 2 * chart_pad)

    def y_coord(value: float) -> float:
        return height - chart_pad - (value / max_value) * (height - 2 * chart_pad)

    chunks = [
        f'<svg class="chart" viewBox="0 0 {width} {height}" role="img">',
        f'<line x1="{chart_pad}" y1="{height-chart_pad}" x2="{width-chart_pad}" y2="{height-chart_pad}" class="axis"/>',
    ]
    if threshold is not None:
        y = y_coord(threshold)
        chunks.append(
            f'<line x1="{chart_pad}" y1="{y:.1f}" x2="{width-chart_pad}" y2="{y:.1f}" class="threshold"/>'
        )
    for index, (label, data, color) in enumerate(series):
        coordinates = " ".join(f"{x_coord(ts):.1f},{y_coord(value):.1f}" for ts, value in data)
        chunks.append(
            f'<polyline points="{coordinates}" fill="none" stroke="{color}" stroke-width="3"/>'
        )
        chunks.append(
            f'<text x="{chart_pad + index * 100}" y="16" fill="{color}" class="legend">{html.escape(label)}</text>'
        )
    chunks.append("</svg>")
    return "".join(chunks)


def _metric(label: str, value: str) -> str:
    return f'<div class="metric"><span>{html.escape(label)}</span><strong>{html.escape(value)}</strong></div>'


def render_dashboard() -> str:
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))["dashboard"]
    thresholds = {
        panel["id"]: float(panel["threshold"]["value"]) for panel in config["panels"]
    }
    if CHALLENGE_PATH.exists():
        try:
            challenge = json.loads(CHALLENGE_PATH.read_text(encoding="utf-8"))
            thresholds["latency"] = float(challenge["latency_threshold_ms"])
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            pass
    records = _load_records()
    end = records[-1]["_ts"] if records else datetime.now(timezone.utc)
    start = end - timedelta(minutes=int(config["time_range_minutes"]))
    records = [record for record in records if record["_ts"] >= start]

    requests = [record for record in records if record.get("event") == "request_received"]
    responses = [record for record in records if record.get("event") == "response_sent"]
    failures = [record for record in records if record.get("event") == "request_failed"]
    latency = [_number(record, "latency_ms") for record in responses]
    ttft = [_number(record, "ttft_ms") for record in responses]

    traffic_buckets: Counter[datetime] = Counter(_minute(record["_ts"]) for record in requests)
    cost_buckets: defaultdict[datetime, float] = defaultdict(float)
    request_buckets: Counter[datetime] = Counter()
    failure_buckets: Counter[datetime] = Counter()
    retrieval_total: Counter[datetime] = Counter()
    retrieval_success: Counter[datetime] = Counter()
    for record in records:
        bucket = _minute(record["_ts"])
        if record.get("event") == "request_received":
            request_buckets[bucket] += 1
        elif record.get("event") == "request_failed":
            failure_buckets[bucket] += 1
        if record.get("event") == "response_sent":
            cost_buckets[bucket] += _number(record, "cost_usd")
        if record.get("tool_success") is not None:
            retrieval_total[bucket] += 1
            retrieval_success[bucket] += int(bool(record.get("tool_success")))

    error_rate = len(failures) / len(requests) * 100 if requests else 0.0
    retrieval_count = sum(retrieval_total.values())
    retrieval_rate = sum(retrieval_success.values()) / retrieval_count * 100 if retrieval_count else 0.0
    total_cost = sum(_number(record, "cost_usd") for record in responses)
    tokens_in = int(sum(_number(record, "tokens_in") for record in responses))
    tokens_out = int(sum(_number(record, "tokens_out") for record in responses))
    qualities = [_number(record, "quality_score") for record in responses]
    quality_avg = sum(qualities) / len(qualities) if qualities else 0.0
    error_types = Counter(str(record.get("error_type", "Unknown")) for record in failures)

    latency_chart = _series_svg(
        [
            ("Latency", [(r["_ts"], _number(r, "latency_ms")) for r in responses], "#8b5cf6"),
            ("TTFT", [(r["_ts"], _number(r, "ttft_ms")) for r in responses], "#22c55e"),
        ],
        threshold=thresholds["latency"],
    )
    traffic_chart = _series_svg(
        [("Requests/min", sorted(traffic_buckets.items()), "#38bdf8")],
        threshold=thresholds["traffic"],
    )
    error_minutes = sorted(set(request_buckets) | set(failure_buckets) | set(retrieval_total))
    error_chart = _series_svg(
        [
            (
                "Error %",
                [(m, failure_buckets[m] / request_buckets[m] * 100 if request_buckets[m] else 0) for m in error_minutes],
                "#ef4444",
            ),
            (
                "Retrieval %",
                [(m, retrieval_success[m] / retrieval_total[m] * 100 if retrieval_total[m] else 0) for m in error_minutes],
                "#22c55e",
            ),
        ],
        threshold=thresholds["errors"],
    )
    cost_chart = _series_svg([("Cost/min", sorted(cost_buckets.items()), "#f59e0b")])
    quality_chart = _series_svg(
        [("Quality", [(r["_ts"], _number(r, "quality_score")) for r in responses], "#14b8a6")],
        threshold=thresholds["quality"],
    )

    panels = [
        f'''<section class="panel" id="latency"><h2>1. Latency percentiles and TTFT</h2>
        <div class="metrics">{_metric("P50", f"{_percentile(latency, 50):.0f} ms")}{_metric("P95", f"{_percentile(latency, 95):.0f} ms")}{_metric("P99", f"{_percentile(latency, 99):.0f} ms")}{_metric("TTFT P95", f"{_percentile(ttft, 95):.0f} ms")}</div>
        {latency_chart}<p class="rule">Threshold line: P95 ≤ {thresholds['latency']:.0f} ms</p></section>''',
        f'''<section class="panel" id="traffic"><h2>2. Request traffic</h2>
        <div class="metrics">{_metric("Total", str(len(requests)))}{_metric("Average", f"{(sum(traffic_buckets.values()) / max(len(traffic_buckets), 1)):.1f} req/min")}</div>
        {traffic_chart}<p class="rule">Expected traffic ≥ {thresholds['traffic']:.0f} request/min</p></section>''',
        f'''<section class="panel" id="errors"><h2>3. Error rate and retrieval success</h2>
        <div class="metrics">{_metric("Error rate", f"{error_rate:.2f}%")}{_metric("Retrieval success", f"{retrieval_rate:.2f}%")}</div>
        {error_chart}<p class="rule">Error threshold ≤ {thresholds['errors']:.0f}% · Retrieval target ≥ 90%</p>
        <p class="detail">Breakdown: {html.escape(str(dict(error_types)) if error_types else 'No errors')}</p></section>''',
        f'''<section class="panel" id="cost"><h2>4. Cost over time</h2>
        <div class="metrics">{_metric("Total cost", f"${total_cost:.6f}")}</div>
        {cost_chart}<p class="rule">Window budget ≤ ${thresholds['cost']:.2f}</p></section>''',
        f'''<section class="panel" id="tokens"><h2>5. Input and output tokens</h2>
        <div class="metrics">{_metric("Input", f"{tokens_in:,} tokens")}{_metric("Output", f"{tokens_out:,} tokens")}</div>
        <div class="bars"><div style="width:{min(tokens_in / max(thresholds['tokens'], 1) * 100, 100):.1f}%">Input</div><div style="width:{min(tokens_out / max(thresholds['tokens'], 1) * 100, 100):.1f}%">Output</div></div>
        <p class="rule">Combined guardrail ≤ {thresholds['tokens']:,.0f} tokens</p></section>''',
        f'''<section class="panel" id="quality"><h2>6. Quality proxy</h2>
        <div class="metrics">{_metric("Average quality", f"{quality_avg:.2f} score")}</div>
        {quality_chart}<p class="rule">Quality target ≥ {thresholds['quality']:.2f}</p></section>''',
    ]

    return f'''<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="refresh" content="{config['refresh_seconds']}">
    <title>{html.escape(config['title'])}</title><style>
    :root{{--bg:#090d16;--card:#111827;--border:#253047;--text:#e5e7eb;--muted:#94a3b8;--accent:#8b5cf6}}
    *{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--text);font:14px Inter,Segoe UI,sans-serif}}
    main{{max-width:1500px;margin:auto;padding:24px}} header{{display:flex;justify-content:space-between;align-items:end;margin-bottom:18px}}
    h1{{margin:0;font-size:30px}} h2{{font-size:17px;margin:0 0 14px}} .subtitle,.rule,.detail{{color:var(--muted)}}
    .grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}} .panel{{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:17px;min-height:310px}}
    .metrics{{display:flex;gap:10px;flex-wrap:wrap}} .metric{{background:#0b1220;border:1px solid var(--border);border-radius:9px;padding:10px 13px;min-width:120px}}
    .metric span{{display:block;color:var(--muted);font-size:12px}} .metric strong{{font-size:20px}} .chart{{width:100%;height:170px;margin-top:12px;background:#0b1220;border-radius:8px}}
    .axis{{stroke:#475569}} .threshold{{stroke:#ef4444;stroke-width:2;stroke-dasharray:7 5}} .legend{{font-size:11px}} .empty{{height:170px;display:grid;place-items:center;color:var(--muted)}}
    .bars div{{background:var(--accent);margin:12px 0;padding:8px;min-width:75px;border-radius:5px}} .status{{color:#22c55e}}
    @media(max-width:900px){{.grid{{grid-template-columns:1fr}}}}
    </style></head><body><main><header><div><h1>{html.escape(config['title'])}</h1>
    <p class="subtitle">Source: data/logs.jsonl · Time range: {config['time_range_minutes']} minutes · Auto-refresh: {config['refresh_seconds']} seconds</p></div>
    <div><span class="status">● Live</span><br>{start:%Y-%m-%d %H:%M} → {end:%H:%M UTC}</div></header>
    <div class="grid">{''.join(panels)}</div></main></body></html>'''
