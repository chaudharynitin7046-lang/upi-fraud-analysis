"""
UPI Digital Payments Fraud & Trends Analysis
--------------------------------------------
Synthetic transaction data generator.
Deterministic (seed=42). ~15,000 rows, Jan-Sep 2026.
Fraud patterns (realistic):
  - Unusual hours (1-5 AM)
  - Round amounts (multiples of 500/1000)
  - New/unusual device types
  - High velocity (many txns in a short window)
Target fraud rate ~1.5%.
"""
import csv
import random
from datetime import datetime, timedelta

SEED = 42
N_ROWS = 15_000
FRAUD_TARGET = 0.009  # base rate; velocity bursts add the rest -> total lands ~1.5%

random.seed(SEED)

MERCHANT_CATS = ["grocery", "fuel", "recharge", "transfer", "shopping"]
CITY_TIERS = ["1", "2", "3"]
DEVICES = ["android", "ios", "web"]

# 2000 unique users
USERS = [f"U{str(i).zfill(5)}" for i in range(1, 2001)]

START = datetime(2026, 1, 1)
END = datetime(2026, 10, 1)  # exclusive -> covers Jan-Sep 2026
SPAN_SECONDS = int((END - START).total_seconds())

# Each user gets a "home" device (their usual device) so fraud can use a NEW device
user_home_device = {u: random.choice(["android", "ios"]) for u in USERS}

# Amount profile per merchant category (median-ish, lognormal-ish via random)
def legit_amount(merchant):
    base = {
        "grocery": 800,
        "fuel": 1500,
        "recharge": 299,
        "transfer": 5000,
        "shopping": 2500,
    }[merchant]
    # lognormal-ish spread, floor at 10
    amt = int(random.lognormvariate(0, 0.9) * base)
    return max(10, amt)

def random_timestamp():
    secs = random.randint(0, SPAN_SECONDS)
    return START + timedelta(seconds=secs)

def is_round_amount(amt):
    return amt % 500 == 0 and amt >= 1000

rows = []
n_fraud_target = int(N_ROWS * FRAUD_TARGET)
n_fraud = 0

txn_id = 0
while len(rows) < N_ROWS:
    txn_id += 1
    user = random.choice(USERS)
    merchant = random.choice(MERCHANT_CATS)
    city = random.choice(CITY_TIERS)
    want_fraud = (n_fraud < n_fraud_target) and (random.random() < 0.02)

    if want_fraud:
        # --- Fraudulent transaction: stack suspicious signals ---
        ts = random_timestamp()
        # 60% chance: move to 1-5 AM window
        if random.random() < 0.60:
            ts = ts.replace(hour=random.randint(1, 5), minute=random.randint(0, 59))
        # 55% chance: round amount
        if random.random() < 0.55:
            amt = random.choice([1000, 2000, 5000, 10000, 20000, 50000])
        else:
            amt = legit_amount(merchant)
        # 50% chance: new device (not the user's usual device)
        if random.random() < 0.50:
            device = random.choice([d for d in DEVICES if d != user_home_device[user]])
        else:
            device = user_home_device[user]
        is_fraud = 1
        n_fraud += 1
    else:
        ts = random_timestamp()
        amt = legit_amount(merchant)
        # occasional legit round amounts (people do send 1000/5000) - noise
        device = user_home_device[user] if random.random() < 0.92 else random.choice(DEVICES)
        is_fraud = 0

    rows.append({
        "txn_id": f"T{str(txn_id).zfill(6)}",
        "user_id": user,
        "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
        "amount_inr": amt,
        "merchant_category": merchant,
        "city_tier": city,
        "device_type": device,
        "is_fraud": is_fraud,
    })

# --- Velocity bursts: add extra fraud bursts so velocity features look real ---
# Add a few users with 6-10 rapid-fire txns within one hour (all fraud)
burst_users = random.sample(USERS, 12)
extra = []
for bu in burst_users:
    base_ts = random_timestamp().replace(minute=0, second=0, microsecond=0)
    n_burst = random.randint(6, 10)
    for i in range(n_burst):
        txn_id += 1
        ts = base_ts + timedelta(minutes=random.randint(0, 55))
        extra.append({
            "txn_id": f"T{str(txn_id).zfill(6)}",
            "user_id": bu,
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "amount_inr": random.choice([1000, 2000, 5000, 10000]),
            "merchant_category": "transfer",
            "city_tier": random.choice(CITY_TIERS),
            "device_type": "web" if user_home_device[bu] != "web" else "android",
            "is_fraud": 1,
        })
rows.extend(extra)

# Shuffle so txns aren't ordered by generation
random.shuffle(rows)

with open("data/transactions.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["txn_id", "user_id", "timestamp", "amount_inr",
                                     "merchant_category", "city_tier", "device_type", "is_fraud"])
    w.writeheader()
    w.writerows(rows)

print(f"Wrote {len(rows)} rows")
print(f"Fraud rows: {sum(r['is_fraud'] for r in rows)} "
      f"({sum(r['is_fraud'] for r in rows)/len(rows)*100:.2f}%)")
