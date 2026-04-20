"""Generate static HTML dashboard from SIA analysis data."""
import html
import json
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
STATIC_DIR = Path(__file__).parent / "static"


def load_data():
    analysis_path = DATA_DIR / "latest_analysis.json"
    ledger_path = DATA_DIR / "prediction_ledger.json"

    analysis = json.loads(analysis_path.read_text(encoding="utf-8")) if analysis_path.exists() else None
    ledger = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else {"predictions": []}
    return analysis, ledger


def _escape(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _human_date(value: str) -> str:
    if not value:
        return "Unknown"
    raw = str(value).strip()
    candidates = [raw]
    if raw.endswith("Z"):
        candidates.append(raw[:-1] + "+00:00")
    if len(raw) == 10:
        candidates.append(f"{raw}T00:00:00+00:00")
    for candidate in candidates:
        try:
            dt = datetime.fromisoformat(candidate)
            return dt.strftime("%d %b %Y")
        except ValueError:
            continue
    return raw


def _status_badge(status: str) -> str:
    status_value = (status or "open").strip().lower()
    css_class = {
        "validated": "validated",
        "falsified": "falsified",
        "expired": "expired",
        "open": "open",
    }.get(status_value, "expired")
    return f'<span class="status-pill {css_class}">{_escape(status_value)}</span>'


def _table_empty(colspan: int, message: str) -> str:
    return f'<tr><td colspan="{colspan}" class="empty-state">{_escape(message)}</td></tr>'


def generate_html(analysis, ledger):
    """Build the full single-file dashboard HTML."""
    analysis = analysis or {}
    ledger = ledger or {"predictions": []}

    root_causes = analysis.get("root_causes", [])
    stories = analysis.get("stories", [])
    predictions = ledger.get("predictions", [])
    latest_updated = analysis.get("analyzed_at") or ledger.get("last_updated") or analysis.get("collected_at", "")

    root_causes_rows = []
    for index, cause in enumerate(root_causes, start=1):
        root_causes_rows.append(
            """
            <tr>
              <td data-sort="{rank}">{rank}</td>
              <td>{target}</td>
              <td><span class="severity-pill severity-{severity_class}">{severity}</span></td>
              <td data-sort="{signal_count}">{signal_count}</td>
              <td>{rationale}</td>
            </tr>
            """.format(
                rank=index,
                target=_escape(cause.get("target", "Unknown")),
                severity=_escape(cause.get("severity", "unknown")),
                severity_class=_escape((cause.get("severity") or "unknown").lower()),
                signal_count=int(cause.get("signal_count", 0) or 0),
                rationale=_escape(cause.get("rationale", "")),
            ).strip()
        )
    if not root_causes_rows:
        root_causes_rows = [_table_empty(5, "No prioritized root causes are available yet.")]

    stories_rows = []
    for story in stories:
        title = _escape(story.get("title", "Untitled"))
        url = _escape(story.get("url", ""))
        link = f'<a href="{url}" target="_blank" rel="noreferrer">{title}</a>' if url else title
        stories_rows.append(
            """
            <tr>
              <td>{title_link}</td>
              <td>{source}</td>
              <td>{published}</td>
            </tr>
            """.format(
                title_link=link,
                source=_escape(story.get("source", "Unknown")),
                published=_escape(_human_date(story.get("published", ""))),
            ).strip()
        )
    if not stories_rows:
        stories_rows = [_table_empty(3, "No stories were attached to this analysis.")]

    predictions_rows = []
    for prediction in predictions:
        notes = prediction.get("validation_notes") or prediction.get("rationale") or ""
        predictions_rows.append(
            """
            <tr data-status="{status_value}">
              <td data-sort="{created_raw}">{created}</td>
              <td>{root_cause}</td>
              <td><span class="severity-pill severity-{severity_class}">{severity}</span></td>
              <td>{status_badge}</td>
              <td>{notes}</td>
            </tr>
            """.format(
                created_raw=_escape(prediction.get("created_at", "")),
                created=_escape(_human_date(prediction.get("created_at", ""))),
                root_cause=_escape(prediction.get("root_cause", "Unknown")),
                severity=_escape(prediction.get("severity", "unknown")),
                severity_class=_escape((prediction.get("severity") or "unknown").lower()),
                status_value=_escape((prediction.get("status") or "open").lower()),
                status_badge=_status_badge(prediction.get("status", "open")),
                notes=_escape(notes),
            ).strip()
        )
    if not predictions_rows:
        predictions_rows = [_table_empty(5, "No predictions have been logged yet.")]

    summary_cards = [
        ("Signals analysed", analysis.get("signal_count", 0)),
        ("Root causes", analysis.get("chosen_count", len(root_causes))),
        ("Predictions logged", len(predictions)),
        ("Adapter", (analysis.get("adapter") or "unknown").upper()),
    ]
    summary_markup = "\n".join(
        f'<div class="summary-card"><div class="summary-label">{_escape(label)}</div><div class="summary-value">{_escape(value)}</div></div>'
        for label, value in summary_cards
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SIA — Systemic Intelligence Analysis</title>
  <style>
    :root {{
      --bg: #1a1a2e;
      --panel: #232946;
      --panel-alt: #1f2440;
      --text: #f4f7fb;
      --muted: #b8c1ec;
      --accent: #4361ee;
      --accent-soft: rgba(67, 97, 238, 0.18);
      --border: rgba(184, 193, 236, 0.2);
      --validated: #2ecc71;
      --falsified: #ef476f;
      --open: #ffd166;
      --expired: #8d99ae;
      --major: #ff8fab;
      --moderate: #ffd166;
      --minor: #90caf9;
      --cosmetic: #adb5bd;
      --existential: #ef476f;
      --unknown: #8d99ae;
      --shadow: 0 18px 40px rgba(0, 0, 0, 0.25);
      --radius: 18px;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
      background: linear-gradient(180deg, #151528 0%, var(--bg) 40%, #111322 100%);
      color: var(--text);
      line-height: 1.6;
    }}
    a {{ color: #8fb4ff; }}
    a:hover {{ color: #b9d0ff; }}
    .page {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }}
    .hero {{
      display: grid;
      gap: 18px;
      margin-bottom: 28px;
      padding: 28px;
      border: 1px solid var(--border);
      border-radius: 24px;
      background: radial-gradient(circle at top right, rgba(67, 97, 238, 0.22), transparent 34%), var(--panel);
      box-shadow: var(--shadow);
    }}
    .eyebrow {{
      color: var(--accent);
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      font-size: 0.8rem;
    }}
    h1, h2, h3 {{ margin: 0; }}
    h1 {{
      font-size: clamp(2rem, 5vw, 3.2rem);
      line-height: 1.1;
    }}
    .subtitle {{
      max-width: 820px;
      color: var(--muted);
      margin: 0;
    }}
    .updated-at {{
      color: var(--muted);
      font-size: 0.95rem;
    }}
    .summary-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 14px;
    }}
    .summary-card {{
      padding: 16px;
      border-radius: var(--radius);
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid var(--border);
    }}
    .summary-label {{
      color: var(--muted);
      font-size: 0.86rem;
      margin-bottom: 8px;
    }}
    .summary-value {{
      font-size: 1.45rem;
      font-weight: 700;
    }}
    .section {{
      margin-top: 24px;
      padding: 24px;
      border: 1px solid var(--border);
      border-radius: 22px;
      background: var(--panel-alt);
      box-shadow: var(--shadow);
    }}
    .section-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 12px;
      margin-bottom: 16px;
      flex-wrap: wrap;
    }}
    .section-copy {{
      color: var(--muted);
      margin: 8px 0 0;
      max-width: 850px;
    }}
    .meta-chip {{
      padding: 8px 12px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: #dbe4ff;
      border: 1px solid rgba(67, 97, 238, 0.35);
      font-size: 0.9rem;
    }}
    .controls {{
      display: flex;
      justify-content: flex-end;
      gap: 10px;
      flex-wrap: wrap;
      margin-bottom: 12px;
    }}
    .control {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      color: var(--muted);
      font-size: 0.95rem;
    }}
    select {{
      background: rgba(255, 255, 255, 0.05);
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 8px 10px;
    }}
    .table-wrap {{
      overflow-x: auto;
      border: 1px solid var(--border);
      border-radius: 16px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      min-width: 640px;
      background: rgba(255, 255, 255, 0.02);
    }}
    th, td {{
      text-align: left;
      padding: 14px 16px;
      border-bottom: 1px solid var(--border);
      vertical-align: top;
    }}
    th {{
      background: rgba(67, 97, 238, 0.12);
      font-size: 0.88rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: #dbe4ff;
      cursor: pointer;
      user-select: none;
      position: sticky;
      top: 0;
    }}
    tbody tr:hover {{
      background: rgba(255, 255, 255, 0.03);
    }}
    .status-pill, .severity-pill {{
      display: inline-flex;
      align-items: center;
      padding: 4px 10px;
      border-radius: 999px;
      font-size: 0.82rem;
      font-weight: 700;
      text-transform: capitalize;
      border: 1px solid transparent;
      white-space: nowrap;
    }}
    .status-pill.validated {{ background: rgba(46, 204, 113, 0.18); color: var(--validated); border-color: rgba(46, 204, 113, 0.4); }}
    .status-pill.falsified {{ background: rgba(239, 71, 111, 0.18); color: var(--falsified); border-color: rgba(239, 71, 111, 0.4); }}
    .status-pill.open {{ background: rgba(255, 209, 102, 0.18); color: var(--open); border-color: rgba(255, 209, 102, 0.4); }}
    .status-pill.expired {{ background: rgba(141, 153, 174, 0.18); color: var(--expired); border-color: rgba(141, 153, 174, 0.35); }}
    .severity-existential {{ background: rgba(239, 71, 111, 0.18); color: var(--existential); border-color: rgba(239, 71, 111, 0.35); }}
    .severity-major {{ background: rgba(255, 143, 171, 0.18); color: var(--major); border-color: rgba(255, 143, 171, 0.35); }}
    .severity-moderate {{ background: rgba(255, 209, 102, 0.18); color: var(--moderate); border-color: rgba(255, 209, 102, 0.35); }}
    .severity-minor {{ background: rgba(144, 202, 249, 0.18); color: var(--minor); border-color: rgba(144, 202, 249, 0.35); }}
    .severity-cosmetic {{ background: rgba(173, 181, 189, 0.18); color: var(--cosmetic); border-color: rgba(173, 181, 189, 0.35); }}
    .severity-unknown {{ background: rgba(141, 153, 174, 0.18); color: var(--unknown); border-color: rgba(141, 153, 174, 0.35); }}
    .empty-state {{
      color: var(--muted);
      text-align: center;
      padding: 24px;
      font-style: italic;
    }}
    .about-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px;
      margin-top: 16px;
    }}
    .about-card {{
      padding: 18px;
      border-radius: 16px;
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid var(--border);
    }}
    footer {{
      margin-top: 28px;
      color: var(--muted);
      text-align: center;
      font-size: 0.95rem;
    }}
    @media (max-width: 700px) {{
      .page {{ padding: 20px 14px 36px; }}
      .hero, .section {{ padding: 18px; border-radius: 18px; }}
      table {{ min-width: 560px; }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <header class="hero">
      <div class="eyebrow">Static dashboard</div>
      <div>
        <h1>SIA — Systemic Intelligence Analysis</h1>
        <p class="subtitle">A static weekly dashboard for batch-ingested news, systemic clustering, and prediction tracking. Everything on this page is generated offline and can be hosted directly on GitHub Pages.</p>
      </div>
      <div class="updated-at">Last updated: {_escape(_human_date(latest_updated))}</div>
      <div class="summary-grid">
        {summary_markup}
      </div>
    </header>

    <section class="section">
      <div class="section-header">
        <div>
          <h2>Latest Analysis</h2>
          <p class="section-copy">Most recent analysis batch collected on {_escape(_human_date(analysis.get("collected_at", "")))} across {_escape(analysis.get("signal_count", 0))} signals.</p>
        </div>
        <div class="meta-chip">Batch run: {_escape(_human_date(analysis.get("analyzed_at", analysis.get("collected_at", ""))))}</div>
      </div>

      <h3>Root causes</h3>
      <div class="table-wrap">
        <table class="sortable">
          <thead>
            <tr>
              <th data-sort-type="number">Rank</th>
              <th>Name</th>
              <th>Severity</th>
              <th data-sort-type="number">Signal count</th>
              <th>Rationale</th>
            </tr>
          </thead>
          <tbody>
            {"".join(root_causes_rows)}
          </tbody>
        </table>
      </div>

      <div style="height:18px"></div>
      <h3>Stories analysed</h3>
      <div class="table-wrap">
        <table class="sortable">
          <thead>
            <tr>
              <th>Title</th>
              <th>Source</th>
              <th>Published</th>
            </tr>
          </thead>
          <tbody>
            {"".join(stories_rows)}
          </tbody>
        </table>
      </div>
    </section>

    <section class="section">
      <div class="section-header">
        <div>
          <h2>Prediction Ledger</h2>
          <p class="section-copy">A running ledger of predicted systemic risks and later validation outcomes.</p>
        </div>
        <div class="meta-chip">Ledger entries: {_escape(len(predictions))}</div>
      </div>

      <div class="controls">
        <label class="control" for="statusFilter">
          Filter status
          <select id="statusFilter">
            <option value="all">All</option>
            <option value="open">Open</option>
            <option value="validated">Validated</option>
            <option value="falsified">Falsified</option>
            <option value="expired">Expired</option>
          </select>
        </label>
      </div>

      <div class="table-wrap">
        <table class="sortable" id="predictionTable">
          <thead>
            <tr>
              <th data-sort-type="date">Date</th>
              <th>Root cause</th>
              <th>Severity</th>
              <th>Status</th>
              <th>Validation notes</th>
            </tr>
          </thead>
          <tbody>
            {"".join(predictions_rows)}
          </tbody>
        </table>
      </div>
    </section>

    <section class="section">
      <div class="section-header">
        <div>
          <h2>About SIA</h2>
          <p class="section-copy">SIA treats headlines as weak signals, not isolated events. The batch pipeline normalizes stories into signals, runs systemic clustering through the analysis pipeline, prioritizes likely root causes under scarcity, and records explicit predictions for later validation.</p>
        </div>
      </div>
      <div class="about-grid">
        <div class="about-card">
          <h3>1. Ingest</h3>
          <p>RSS feeds are fetched in batch, cleaned, deduplicated, and converted into normalized SIA signals.</p>
        </div>
        <div class="about-card">
          <h3>2. Analyze</h3>
          <p>The SIA pipeline scores each signal, clusters repeated failure patterns, and prioritizes likely systemic roots.</p>
        </div>
        <div class="about-card">
          <h3>3. Track</h3>
          <p>Each prioritized root cause becomes a prediction entry with severity, rationale, and validation status over time.</p>
        </div>
      </div>
    </section>

    <footer>
      Powered by SIA — predictions are systemic analysis, not financial or political advice.
    </footer>
  </div>

  <script>
    (function() {{
      function getCellValue(row, index) {{
        const cell = row.children[index];
        return (cell && (cell.dataset.sort || cell.textContent || "")).trim().toLowerCase();
      }}

      document.querySelectorAll("table.sortable").forEach(function(table) {{
        const headers = table.querySelectorAll("th");
        headers.forEach(function(header, index) {{
          let ascending = true;
          header.addEventListener("click", function() {{
            const tbody = table.tBodies[0];
            const rows = Array.from(tbody.querySelectorAll("tr"));
            const sortType = header.dataset.sortType || "text";
            rows.sort(function(a, b) {{
              const aValue = getCellValue(a, index);
              const bValue = getCellValue(b, index);
              if (sortType === "number") {{
                return (parseFloat(aValue) || 0) - (parseFloat(bValue) || 0);
              }}
              if (sortType === "date") {{
                return Date.parse(aValue || 0) - Date.parse(bValue || 0);
              }}
              return aValue.localeCompare(bValue);
            }});
            if (!ascending) {{
              rows.reverse();
            }}
            ascending = !ascending;
            rows.forEach(function(row) {{ tbody.appendChild(row); }});
          }});
        }});
      }});

      const filter = document.getElementById("statusFilter");
      const predictionRows = Array.from(document.querySelectorAll("#predictionTable tbody tr"));
      if (filter) {{
        filter.addEventListener("change", function() {{
          const selected = filter.value;
          predictionRows.forEach(function(row) {{
            if (selected === "all" || row.dataset.status === selected) {{
              row.style.display = "";
            }} else {{
              row.style.display = "none";
            }}
          }});
        }});
      }}
    }})();
  </script>
</body>
</html>
"""


def main():
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    analysis, ledger = load_data()

    if not analysis:
        print("No analysis data found. Run run_analysis.py first.")
        return

    html_content = generate_html(analysis, ledger)
    outfile = STATIC_DIR / "index.html"
    outfile.write_text(html_content, encoding="utf-8")
    print(f"Generated: {outfile}")


if __name__ == "__main__":
    main()
