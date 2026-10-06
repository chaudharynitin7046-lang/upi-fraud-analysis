"""
UPI Digital Payments — Fraud & Trends Analysis
==============================================
Loads the synthetic transaction data, runs EDA, builds a simple rule-based
fraud detector, evaluates it (precision/recall) and saves charts.

Run:  ~/workspace/.venv/bin/python analysis.py   (from this directory)
"""
import os

import matplotlib
matplotlib.use("Agg")  # headless: write PNGs without a display
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

DATA_PATH = "data/transactions.csv"
CHART_DIR = "charts"
os.makedirs(CHART_DIR, exist_ok=True)

# ---------------------------------------------------------------- load + prep
df = pd.read_csv(DATA_PATH)
df["timestamp"] = pd.to_datetime(df["timestamp"])
df["hour"] = df["timestamp"].dt.hour
df["month"] = df["timestamp"].dt.to_period("M").astype(str)
df["is_round_amount"] = (df["amount_inr"] % 500 == 0) & (df["amount_inr"] >= 1000)
df["is_night"] = df["hour"].between(1, 5)
# Proxy for "new/unusual device": in this dataset users overwhelmingly transact
# from android/ios; 'web' is rare for legit users and common in fraud bursts.
df["is_unusual_device"] = df["device_type"] == "web"

fraud = df[df["is_fraud"] == 1]
legit = df[df["is_fraud"] == 0]

print("=" * 60)
print("UPI FRAUD & TRENDS ANALYSIS  (Jan-Sep 2026, synthetic data)")
print("=" * 60)
print(f"Total transactions : {len(df):,}")
print(f"Fraud transactions : {len(fraud):,} ({len(fraud)/len(df)*100:.2f}%)")
print(f"Unique users       : {df['user_id'].nunique():,}")
print(f"Date range         : {df['timestamp'].min().date()} to {df['timestamp'].max().date()}")
print()

# ------------------------------------------------- 1. hourly fraud pattern
hourly = df.groupby("hour").agg(total=("is_fraud", "size"),
                                fraud_n=("is_fraud", "sum"))
hourly["fraud_rate_pct"] = 100 * hourly["fraud_n"] / hourly["total"]
peak_hour = hourly["fraud_rate_pct"].idxmax()
night_rate = df[df["is_night"]]["is_fraud"].mean() * 100
day_rate = df[~df["is_night"]]["is_fraud"].mean() * 100
print(f"[1] Peak fraud hour: {peak_hour}:00 ({hourly.loc[peak_hour, 'fraud_rate_pct']:.2f}% fraud rate)")
print(f"    Night (1-5 AM) fraud rate: {night_rate:.2f}% vs rest of day: {day_rate:.2f}% "
      f"({night_rate/max(day_rate, 1e-9):.1f}x higher)")

# -------------------------------------------- 2. fraud by merchant category
cat = df.groupby("merchant_category").agg(total=("is_fraud", "size"),
                                          fraud_n=("is_fraud", "sum"))
cat["fraud_rate_pct"] = 100 * cat["fraud_n"] / cat["total"]
cat = cat.sort_values("fraud_rate_pct", ascending=False)
print("\n[2] Fraud rate by merchant category:")
for m, r in cat.iterrows():
    print(f"    {m:<10} {r['fraud_rate_pct']:.2f}%  ({int(r['fraud_n'])}/{int(r['total'])})")

# --------------------------------------- 3. amount: fraud vs legit
print(f"\n[3] Median amount — fraud: ₹{fraud['amount_inr'].median():,.0f} | "
      f"legit: ₹{legit['amount_inr'].median():,.0f}")
print(f"    Round-amount share — fraud: {fraud['is_round_amount'].mean()*100:.1f}% | "
      f"legit: {legit['is_round_amount'].mean()*100:.1f}%")

# --------------------------------------- 4. rule-based fraud detector
# Rule: night-time AND round amount AND unusual device -> flag as fraud
df["rule_flag"] = df["is_night"] & df["is_round_amount"] & df["is_unusual_device"]
tp = int(((df["rule_flag"] == 1) & (df["is_fraud"] == 1)).sum())
fp = int(((df["rule_flag"] == 1) & (df["is_fraud"] == 0)).sum())
fn = int(((df["rule_flag"] == 0) & (df["is_fraud"] == 1)).sum())
precision = tp / (tp + fp) if (tp + fp) else 0
recall = tp / (tp + fn) if (tp + fn) else 0
print("\n[4] Rule-based detector: (1-5 AM) AND (round amount) AND (unusual device)")
print(f"    Flagged: {tp + fp:,} | True positives: {tp} | False positives: {fp} | Missed fraud: {fn}")
print(f"    Precision: {precision*100:.1f}%   Recall: {recall*100:.1f}%")

# ------------------------------------------------- 5. monthly trend
monthly = df.groupby("month").agg(total=("is_fraud", "size"),
                                  fraud_n=("is_fraud", "sum"))
monthly["fraud_rate_pct"] = 100 * monthly["fraud_n"] / monthly["total"]
print("\n[5] Monthly fraud rate trend:")
for m, r in monthly.iterrows():
    print(f"    {m}  {r['fraud_rate_pct']:.2f}%")

# ================================================================== charts
plt.style.use("seaborn-v0_8-whitegrid")

# Chart 1: fraud rate by hour (line)
fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(hourly.index, hourly["fraud_rate_pct"], marker="o", linewidth=2, color="#c0392b")
ax.axvspan(1, 5, color="#c0392b", alpha=0.08, label="High-risk window (1-5 AM)")
ax.set_title("Fraud Rate by Hour of Day — UPI Transactions (Jan-Sep 2026)")
ax.set_xlabel("Hour of day")
ax.set_ylabel("Fraud rate (%)")
ax.set_xticks(range(0, 24))
ax.legend()
fig.tight_layout()
fig.savefig(f"{CHART_DIR}/fraud_by_hour.png", dpi=150)
plt.close(fig)

# Chart 2: amount distribution fraud vs legit (boxplot, log scale)
fig, ax = plt.subplots(figsize=(8, 5))
ax.boxplot([legit["amount_inr"], fraud["amount_inr"]],
           tick_labels=["Legit", "Fraud"], patch_artist=True,
           boxprops=dict(facecolor="#d5e8ff"), medianprops=dict(color="#1a5276", linewidth=2))
ax.set_yscale("log")
ax.set_title("Transaction Amount Distribution: Fraud vs Legit (log scale)")
ax.set_ylabel("Amount (INR, log scale)")
fig.tight_layout()
fig.savefig(f"{CHART_DIR}/amount_boxplot.png", dpi=150)
plt.close(fig)

# Chart 3: monthly trend — volume bars + fraud-rate line
fig, ax1 = plt.subplots(figsize=(10, 5))
ax1.bar(monthly.index, monthly["total"], color="#aed6f1", label="Total txns")
ax1.set_xlabel("Month")
ax1.set_ylabel("Transaction volume", color="#1a5276")
ax1.tick_params(axis="x", rotation=30)
ax2 = ax1.twinx()
ax2.plot(monthly.index, monthly["fraud_rate_pct"], marker="o", color="#c0392b",
         linewidth=2, label="Fraud rate %")
ax2.set_ylabel("Fraud rate (%)", color="#c0392b")
ax1.set_title("Monthly Transaction Volume & Fraud Rate Trend")
fig.tight_layout()
fig.savefig(f"{CHART_DIR}/monthly_trend.png", dpi=150)
plt.close(fig)

print(f"\nCharts saved to {CHART_DIR}/: fraud_by_hour.png, amount_boxplot.png, monthly_trend.png")
print("=" * 60)
