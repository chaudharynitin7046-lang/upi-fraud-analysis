# UPI Digital Payments — Fraud & Trends Analysis (India)

An end-to-end data analysis project on **15,098 synthetic UPI transactions (Jan–Sep 2026)**:
SQL fraud detection queries, Python EDA, a rule-based fraud detector with
precision/recall evaluation, and publication-ready charts.

> **Note:** All data is synthetically generated (`gen_data.py`, seed=42) for
> portfolio purposes. No real user data is used.

## Problem Statement

Digital fraud on UPI rails is growing in India. A payments risk team needs to
know: *when* does fraud happen, *where* (which merchant categories), *what it
looks like* (amount patterns), and whether a few simple, explainable rules can
catch it before money moves. This project answers those questions.

## Dataset

`data/transactions.csv` — 15,098 rows × 8 columns, generated deterministically
(`seed=42`; re-run `gen_data.py` to reproduce byte-identical data).

| Column | Description |
|---|---|
| `txn_id` | Unique transaction ID |
| `user_id` | Anonymised user (1,999 users) |
| `timestamp` | Transaction time, Jan–Sep 2026 |
| `amount_inr` | Transaction amount in INR |
| `merchant_category` | grocery / fuel / recharge / transfer / shopping |
| `city_tier` | 1 / 2 / 3 |
| `device_type` | android / ios / web |
| `is_fraud` | 1 = fraud (233 rows, **1.54%**), 0 = legit |

Fraud was engineered to look realistic: concentrated in **1–5 AM**, **round
amounts** (₹1,000/₹5,000/₹10,000…), **unusual devices**, and **velocity bursts**
(6–10 rapid transfers from one user inside an hour).

## Methodology

1. **Data generation** — `gen_data.py`: deterministic synthetic data with
   planted fraud signals + velocity bursts.
2. **SQL fraud queries** — `sql/fraud_queries.sql`: 5 advanced queries using
   CTEs and window functions (fraud rate by hour, by merchant category,
   rolling 1-hour velocity flags via self-join, per-user z-score amount
   outliers, monthly trend with `LAG()` MoM change).
3. **Python analysis** — `analysis.py`: pandas EDA, hourly/category/amount
   patterns, a rule-based detector, precision/recall evaluation, 3 charts.

## Key Findings

1. **Fraud is 3.3× more likely at night.** Transactions between 1–5 AM have a
   3.43% fraud rate vs 1.03% for the rest of the day; the single riskiest hour
   is 5 AM (5.02%).
2. **Money-transfer is the riskiest category** at 4.22% fraud rate (130 of
   3,083 transfers) — ~7× grocery (0.61%). Fraudsters move money, they don't
   shop.
3. **Round amounts are a near-perfect fraud tell.** 72.5% of fraud transactions
   are round amounts (≥₹1,000, multiple of ₹500) vs only 0.1% of legit ones.
   Median fraud amount is ₹5,000 vs ₹1,409 legit.
4. **A 3-signal rule catches fraud with 100% precision.** Flagging
   (1–5 AM) AND (round amount) AND (unusual device) flagged 27 transactions —
   all 27 were real fraud (precision 100%), but it only caught 11.6% of all
   fraud (recall 11.6%): fraudsters who skip one signal still slip through.
5. **Fraud is spiky, not seasonal.** Monthly fraud rate swung between 0.94%
   (May) and 2.58% (July) with no smooth trend — consistent with campaign-style
   fraud bursts rather than organic growth.

## Recommendations for a Payments Team

1. **Step-up authentication 1–5 AM** for transfers above ₹1,000 — the cheapest
   high-impact control given the 3.3× night multiplier.
2. **Velocity guardrail:** auto-hold accounts doing >5 transfers/hour; the SQL
   velocity query (`Q3`) is production-ready logic for this.
3. **Round-amount + new-device combo** should feed the risk score as a hard
   feature — it has 100% precision in this data.
4. **Boost recall with a model, not more rules:** the rule's 11.6% recall shows
   hand-written rules plateau fast; train a gradient-boosted model on
   hour, amount z-score, velocity, and device-change features next.

## Tools Used

Python (pandas, matplotlib, numpy), SQL (CTEs, window functions — PostgreSQL/SQLite)

## How to Run

```bash
cd upi-fraud-analysis

# (optional) regenerate the synthetic data — deterministic, seed=42
~/workspace/.venv/bin/python gen_data.py

# run the full analysis (prints insights, saves charts to charts/)
~/workspace/.venv/bin/python analysis.py
```

Charts produced: `charts/fraud_by_hour.png`, `charts/amount_boxplot.png`,
`charts/monthly_trend.png`.

## Project Structure

```
upi-fraud-analysis/
├── data/transactions.csv      # synthetic dataset (15,098 rows)
├── sql/fraud_queries.sql      # 5 advanced fraud-detection queries
├── charts/                    # generated PNG charts
├── analysis.py                # EDA + rule-based detector + charts
├── gen_data.py                # deterministic data generator (seed=42)
└── README.md
```
