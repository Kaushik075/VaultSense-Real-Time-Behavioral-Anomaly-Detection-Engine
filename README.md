## VaultSense — Real-Time Behavioral Anomaly Detection Engine

---


## The Problem

Traditional security tools catch known attack signatures. They miss behavioral drift — when a legitimate-looking session does something the real user would never do.

- A bot logs into 847 accounts in 6 minutes — no database error triggered
- A stolen credential logs in from Russia at 3 AM on a new device — pipeline is healthy
- A compromised account downloads every file silently — no anomaly in the data

**The data pipeline is fine. The USER is the anomaly.**

---

## What VaultSense Does

VaultSense monitors user session events in real-time through a 3-layer intelligence pipeline:

**Layer 1 — Rule-Based Fraud Engine**
5 behavioral rules fire simultaneously on every incoming event:
- Velocity spike → more than 15 events in 10 minutes
- Unknown device → device ID not in user's history
- Geographic anomaly → country differs from usual location
- Odd hours activity → login between 2–5 AM
- Transaction spike → amount exceeds 3x user baseline

**Layer 2 — Gemini AI Risk Interpretation**
Flagged events are sent to Google Gemini with full behavioral context. Gemini returns a unique natural language risk assessment per event — no two alerts are identical.

**Layer 3 — Persistence & Alerting**
High-risk events are logged to PostgreSQL and a Slack alert fires to `#security-alerts` in under 5 seconds.

---
<img width="1832" height="500" alt="Image" src="https://github.com/user-attachments/assets/f64a66a9-5e77-44d4-b5fe-7f576c63a599" />

---

## Results

Tested on 250,000 rows of realistic streaming platform data with 3 injected attack patterns:

| Anomaly Type | Injected | Detected | Sample AI Reason |
|---|---|---|---|
| Credential Stuffing | 3,000 | ✅ All | *"Multiple logins from different devices within milliseconds"* |
| Account Takeover | 1,500 | ✅ All | *"Foreign country access with unknown device at 3 AM"* |
| Suspicious Downloads | 800 | ✅ All | *"Rapid consecutive download events outside normal hours"* |

Every Slack alert had a different Gemini-generated reason — contextual reasoning, not rule matching.

---

## Architecture

```
Webhook → Request Validator → Fetch User History (PostgreSQL)
→ Context Builder → Fraud Rules Engine → Gemini AI Interpreter
→ AI Response Cleaner → Risk Decision Combiner → High Risk Filter
→ Database Logger + Slack Alert Dispatcher
```

---

## Tech Stack

| Component | Tool |
|---|---|
| Orchestration | n8n (self-hosted, Docker) |
| Database | PostgreSQL on Neon.tech |
| AI Layer | Google Gemini (gemini-3.5-flash) |
| Alerting | Slack (#security-alerts) |
| Data Generation | Python (psycopg2, uuid, faker) |

---

## Database Schema

**3 tables in PostgreSQL:**

- `user_activity_log` — 250,000 user session events
- `user_behavior_baselines` — normal behavior profiles for 500 users
- `behavioral_audit_log` — permanent audit trail of all detected anomalies

---

<img width="1575" height="690" alt="Image" src="https://github.com/user-attachments/assets/83a3c003-95bf-4bac-9127-612880947304" />

---


<img width="1572" height="753" alt="Image" src="https://github.com/user-attachments/assets/16e0e0d2-8c91-4654-8ed8-291aba767e1c" />


---


## How to Run

**1. Generate Data**
```bash
pip install psycopg2-binary
python vaultsense_generate_data.py
```

Update `DB_HOST`, `DB_PASSWORD` in the script with your Neon credentials.

**2. Import Workflow**
- Open n8n → Import workflow → upload `vaultsense_workflow.json`
- Add credentials: PostgreSQL (Neon) + Google Gemini API + Slack Bot Token
- Activate the workflow

**3. Test**
```bash
Invoke-WebRequest -Uri "http://localhost:5678/webhook/user-activity" `
-Method POST -ContentType "application/json" `
-Body '{"user_id":"user_0001","event_type":"login","device_id":"dev_UNKNOWN_abc123","country":"Russia","events_last_10_mins":25,"hour_of_day":3}' `
-UseBasicParsing
```

Check `#security-alerts` in Slack for the alert.

---

## Project Structure

```
vaultsense/
├── vaultsense_generate_data.py   # Data generation script
├── vaultsense_workflow.json      # n8n workflow export
└── README.md
```

---

## Key Engineering Decisions

- **Bulk inserts over row-by-row** — switched to `psycopg2.extras.execute_values` reducing 250K row load time from 2+ hours to under 3 minutes
- **Gemini over OpenAI** — free tier, no credit card, 15 req/min sufficient for real-time alerting
- **Webhook trigger over scheduled** — processes every event in real-time instead of batch
- **Separate audit log table** — `behavioral_audit_log` maintains permanent incident history independent of the activity log

---

## Related Project

**DriftGuard** — Autonomous Data Quality Observability Agent
Monitors data pipelines for null rates, schema drift, and statistical anomalies.

Together: DriftGuard ensures data reliability. VaultSense ensures behavioral security.

---
