# SIA Daily Intelligence — Deployment Specification

## Overview

Automated daily systemic intelligence analysis deployed on Azure, with three interaction flows:
1. **Daily email** — full analysis inline in email body
2. **Web dashboard** — live at a public URL, behind authentication for Flow 3
3. **Chat agent** — Azure AI Foundry agent for on-demand analysis, behind auth

## Resource Group

- Name: `raviRG`
- Location: `australiasoutheast`

## Flow 1: Daily Automated Analysis

### Schedule
- **6:00 AM AEST daily** (Azure Function Timer trigger)

### Pipeline
1. Collect top stories from RSS feeds (BBC, Al Jazeera, ABC AU, + fallbacks)
2. Send to Azure OpenAI (GPT-4o) for SIA pipeline analysis
3. Generate narrative + root cause table + detail cards + predictions
4. Check prediction ledger for any predictions whose timeline has matured — run auto-validation
5. Generate daily password (24 chars, special characters only, rotated daily)
6. Send email to ravishankar.nandagopalan@microsoft.com containing:
   - Summary section (top root causes, severity, signal count)
   - Full analysis inline (narrative, table, detail cards)
   - Prediction validation results for any matured predictions
   - Today's login password for the chat interface
   - Link to the live dashboard

### Email format
- **Inline HTML** in the email body (not attachment)
- Summary at top, full report below
- Prediction validation section if any predictions matured today
- Daily rotating password for Flow 3 at the bottom

## Flow 2: Web Dashboard

### URL
- `https://<sia-staticwebapp>.azurestaticapps.net`

### Content
- Latest analysis with narrative + table + detail cards
- Prediction ledger with historical tracking (open / validated / falsified / expired)
- Stories analysed with links to sources
- Updated daily by the Function App after each analysis run

### Access
- Public read access for the dashboard (no auth needed for viewing)
- Flow 3 chat interface requires authentication (see below)

## Flow 3: Chat Agent (Behind Auth)

### Authentication
- **Hidden login**: No visible login button on the public site. Access to the chat interface is ONLY via the direct login link in the daily email (contains a time-limited token + password)
- Password: **24 characters, special characters only**, generated fresh daily
- Password delivered in the daily email alongside the login link
- **5 failed login attempts → 4-hour lockout** from that IP, sends a fresh magic login link to the registered email
- Magic link is single-use, expires in 15 minutes

### Anti-bot / Anti-crawl Protection
- `robots.txt` disallows all crawlers (`User-agent: * Disallow: /`)
- `X-Robots-Tag: noindex, nofollow, noarchive` on all responses
- No sitemap published
- No site structure exposed (no directory listing, no API discovery endpoints)
- Rate limiting on all endpoints (10 req/min per IP for dashboard, 3 req/min for auth)
- Block known bot User-Agent patterns
- CSP headers to prevent embedding

### Agent capabilities
- On-demand SIA analysis: "Analyse the impact of X on Y"
- Query prediction ledger: "What predictions are still open?" / "Which predictions were validated?"
- Query past analyses: "What did you find last Tuesday?"
- Runs the full SIA pipeline on-demand when given a new topic

### Implementation
- Azure AI Foundry agent with SIA pipeline tools
- Authentication layer as a lightweight middleware (Azure Function or Static Web App auth)

## Prediction Auto-Validation

### Mechanism
- Each prediction has a `timeline` field (e.g., "6-8 weeks", "3-6 months", "12 months")
- A running log stores: prediction ID, created date, maturity date (computed from timeline), prediction text, falsification criteria
- When a prediction's maturity date arrives:
  1. Collect current news signals related to the prediction's topic
  2. Run SIA analysis on those signals
  3. Compare current state against the prediction and falsification criteria
  4. Mark as `validated`, `falsified`, or `partially_validated`
  5. Include result in the daily email

### Storage
- `prediction_ledger.json` — full ledger with all predictions and their statuses
- `prediction_schedule.json` — upcoming maturity dates for auto-validation triggers

## Azure Resources Required

| Resource | Type | SKU | Purpose |
|----------|------|-----|---------|
| Azure Function App | Microsoft.Web/sites | Consumption (Y1) | Daily timer + pipeline |
| Azure OpenAI | Microsoft.CognitiveServices | S0 | GPT-4o for analysis |
| Azure Communication Services | Microsoft.Communication | Free | Email delivery |
| Azure Static Web App | Microsoft.Web/staticSites | Free | Dashboard hosting |
| Storage Account | Microsoft.Storage | Standard_LRS | Function App storage + data |

## Cost Estimate

| Item | Daily | Monthly |
|------|-------|---------|
| Function App (Consumption) | ~$0 | ~$0 (free tier) |
| Azure OpenAI (20 signals/day) | ~$0.10-0.50 | ~$3-15 |
| Communication Services (1 email/day) | ~$0 | ~$0 (free tier) |
| Static Web App | $0 | $0 (free tier) |
| Storage | ~$0.01 | ~$0.30 |
| **Total** | **~$0.15-0.55** | **~$5-17** |
