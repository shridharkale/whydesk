# WhyDesk — Metric Investigation Agent

WhyDesk is a production-quality metric investigation agent built for business analysts. It uses **Hindsight** (`hindsight-client`) as its long-term institutional memory layer and **Groq** (`groq`) for high-speed tool calling and diagnostic planning.

---

## The Problem

When key revenue or business metrics drop (such as *"Why did revenue drop 18% in the South region last week?"*), stateless agents repeat the same expensive, repetitive diagnostic cycle:
- Re-checking all diagnostic tools in the exact same default order
- Investigating previously ruled-out hypotheses (e.g. blaming competitor promotions or public holidays)
- Misinterpreting recurring pipeline sync stalls (e.g. Monday ETL batch lags) as real revenue loss
- Formatting every answer identically, disregarding stakeholder constraints (e.g. a Finance VP needing a strict 1-line exact dollar summary vs. an analyst needing a deep diagnostic trace)

---

## How WhyDesk Uses Hindsight

WhyDesk integrates Hindsight across three distinct memory types plus reflective planning:

| Memory Type | Usage in WhyDesk | Example |
| :--- | :--- | :--- |
| **Observation** | Confirmed root causes and numerical impacts | *"In 2026-W10 for the South region, confirmed root cause was 20% discount tier auto-applied (-$42,500 WoW)."* |
| **World** | Data pipeline and infrastructure reliability traps | *"Monday revenue drops are often false alarms caused by etl_sales_sync lag; verify ETL health before trusting Monday anomalies."* |
| **Experience** | Stakeholder-specific presentation and formatting rules | *"Finance Head requires a strict 1-line summary containing the exact dollar figure."* |
| **Reflect** | Contextual synthesis to formulate an adaptive tool execution plan | Selects which 1–2 tools to check first, names ruled-out checks to deprioritize, and enforces stakeholder format rules. |

---

## Architecture Diagram

```
                       +-----------------------------+
                       |    Analyst User Query       |
                       +--------------+--------------+
                                      |
                                      v
                       +-----------------------------+
                       |   Hindsight Recall & Reflect |
                       |  - Observation memories     |
                       |  - World memories (ETL)     |
                       |  - Experience (Stakeholder) |
                       +--------------+--------------+
                                      |
                         Recalled context + Plan
                                      |
                                      v
                       +-----------------------------+
                       |   Groq Tool Planner         |
                       |  - Evaluates prior causes   |
                       |  - Skips ruled-out checks   |
                       |  - Orders priority tools    |
                       +--------------+--------------+
                                      |
                          Selective Tool Execution
                                      |
                                      v
         +--------------------------------------------------------+
         |                 5 Diagnostic Tools                     |
         |  1. check_etl_pipeline                                 |
         |  2. check_pricing_changes                              |
         |  3. check_inventory_stockouts                          |
         |  4. check_competitor_promos                            |
         |  5. check_holiday_calendar                             |
         +----------------------------+---------------------------+
                                      |
                        Confirmed Cause & Impact ($)
                                      |
                                      v
                       +-----------------------------+
                       |   Hindsight Retain          |
                       |  - Synchronous retention    |
                       |  - Retains verdict & format |
                       +-----------------------------+
```

---

## Setup & Installation

### 1. Requirements
- Python 3.10+
- `pip install -r requirements.txt`

### 2. Environment Variables
Create `.env` using `.env.example`:
```bash
cp .env.example .env
```
Fill in credentials:
```ini
HINDSIGHT_API_KEY=hsk_...
HINDSIGHT_BASE_URL=https://api.hindsight.vectorize.io
HINDSIGHT_BANK_ID=whydesk-prod-bank
GROQ_API_KEY=gsk_...
GROQ_MODEL=qwen/qwen3-32b
```
*(If `HINDSIGHT_API_KEY` is not provided, WhyDesk automatically runs against an in-memory local simulation backend).*

### 3. Run Smoke Tests & Pytest
```bash
python scripts/smoke_test.py
python -m pytest tests/
```

### 4. Start the Application
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```
Open your browser at `http://localhost:8000`.

---

## Demo Walkthrough (5 Sequential Runs)

1. **Run 1: Cold start (Finance Head, Memory ON)**
   - *Inquiry:* `"Why did revenue drop 18% in the South region in W10, and FYI I only ever want a 1-line summary with the exact dollar impact."`
   - *Behavior:* Recall returns 0 memories (`COLD_START_NO_MEMORIES`). All 5 diagnostic tools run in standard audit order. Confirms 20% discount tier (-$42,500). Retains the verdict and the Finance Head 1-line format preference.

2. **Run 2: Unreliable data source (Senior Analyst, Memory ON)**
   - *Inquiry:* `"Alert says Monday revenue in W11 is down 64% across South. Did pricing break again?"`
   - *Behavior:* Recalls South pricing memory and pipeline history. Checks `check_etl_pipeline`, detects `etl_sales_sync` stall at 02:00 UTC ($88,000 delayed in ETL, $0 real loss). Retains the pipeline reliability trap note.

3. **Run 3: Ruled-out hypotheses (Senior Analyst, Memory ON)**
   - *Inquiry:* `"North hardware bundle revenue dipped 24% in W11. Sales blames a competitor promo or holiday. True?"`
   - *Behavior:* Checks competitor promo (disproves: rival active in West, not North) and holiday calendar (disproves: no holidays). Confirms ENT-GATEWAY-02 stockout (-$31,200). Retains ruled-out hypotheses.

4. **Run 4: Pattern consolidation (Senior Analyst, Memory ON)**
   - *Inquiry:* `"South region revenue dropped 15% again in W12. Investigate."`
   - *Behavior:* Recalls South pricing sensitivity and ETL sanity check. Checks ETL (clean) and pricing (finds SOUTH-Q1-25 promo code reactivation, -$36,800). Skips remaining tools. Consolidates the South pricing pattern.

5. **Run 5: Climax (Finance Head, Memory ON vs. OFF)**
   - *Inquiry:* `"Why did revenue drop 19% in the South region in W13?"`
   - *Memory ON:* Recalls South pattern and Finance Head 1-line constraint. Checks `check_etl_pipeline` (clean) and `check_pricing_changes` (hit: -$47,900 reseller ACV repricing). **Exactly 2 tools run, 3 skipped.** Returns strict 1-line answer:
     > *"The 19% revenue drop in the South region for W13 was caused by a Reseller Master Agreement Amendment (RESELLER-SOUTH-2026) that cut unit ACV by 19%, resulting in an exact dollar impact of -$47,900."*
   - *Memory OFF:* All 5 tools run exhaustively; returns long multi-paragraph diagnostic with no stakeholder format adaptation.

