-- ============================================================================
-- UPI Digital Payments — Fraud & Trends Analysis
-- Advanced SQL: CTEs + window functions
-- Table: transactions(txn_id, user_id, timestamp, amount_inr, merchant_category,
--                      city_tier, device_type, is_fraud)
-- Works on PostgreSQL / SQLite. SQLite note: STDDEV() is not built-in, so the
-- amount-outlier query computes the standard deviation manually from the
-- variance formula: STDDEV = SQRT(AVG(x^2) - AVG(x)^2).
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Q1. Fraud rate by hour of day
-- Which hours are riskiest? (Expect a spike in the 1-5 AM window.)
-- ----------------------------------------------------------------------------
WITH hourly AS (
    SELECT
        CAST(strftime('%H', timestamp) AS INTEGER) AS hour_of_day,
        COUNT(*)                                   AS total_txns,
        SUM(is_fraud)                              AS fraud_txns
    FROM transactions
    GROUP BY 1
)
SELECT
    hour_of_day,
    total_txns,
    fraud_txns,
    ROUND(100.0 * fraud_txns / total_txns, 2) AS fraud_rate_pct,
    RANK() OVER (ORDER BY 1.0 * fraud_txns / total_txns DESC) AS risk_rank
FROM hourly
ORDER BY hour_of_day;

-- ----------------------------------------------------------------------------
-- Q2. Fraud rate by merchant category (with share of all fraud)
-- ----------------------------------------------------------------------------
WITH cat AS (
    SELECT
        merchant_category,
        COUNT(*)      AS total_txns,
        SUM(is_fraud) AS fraud_txns
    FROM transactions
    GROUP BY 1
),
totals AS (
    SELECT SUM(is_fraud) AS all_fraud FROM transactions
)
SELECT
    c.merchant_category,
    c.total_txns,
    c.fraud_txns,
    ROUND(100.0 * c.fraud_txns / c.total_txns, 2)           AS fraud_rate_pct,
    ROUND(100.0 * c.fraud_txns / t.all_fraud, 2)            AS share_of_all_fraud_pct,
    RANK() OVER (ORDER BY 1.0 * c.fraud_txns / c.total_txns DESC) AS risk_rank
FROM cat c
CROSS JOIN totals t
ORDER BY fraud_rate_pct DESC;

-- ----------------------------------------------------------------------------
-- Q3. Velocity check — flag users with > 5 transactions in any rolling hour
-- Uses a self-join on a 1-hour window, then ranks the worst offenders.
-- ----------------------------------------------------------------------------
WITH velocity AS (
    SELECT
        t1.user_id,
        t1.txn_id,
        t1.timestamp,
        COUNT(t2.txn_id) AS txns_in_last_hour
    FROM transactions t1
    JOIN transactions t2
      ON t2.user_id = t1.user_id
     AND t2.timestamp BETWEEN datetime(t1.timestamp, '-1 hour') AND t1.timestamp
    GROUP BY t1.user_id, t1.txn_id, t1.timestamp
),
flagged AS (
    SELECT *
    FROM velocity
    WHERE txns_in_last_hour > 5
)
SELECT
    f.user_id,
    f.txn_id,
    f.timestamp,
    f.txns_in_last_hour,
    SUM(t.is_fraud) OVER (PARTITION BY f.user_id) AS user_total_fraud,
    ROW_NUMBER() OVER (PARTITION BY f.user_id ORDER BY f.timestamp) AS burst_seq
FROM flagged f
JOIN transactions t USING (txn_id)
ORDER BY txns_in_last_hour DESC, f.timestamp;

-- ----------------------------------------------------------------------------
-- Q4. Amount outliers per user — z-score style with windowed AVG / STDDEV
-- Flags transactions whose amount is > 3 std-devs above the user's own mean.
-- (PostgreSQL: replace the manual stddev with STDDEV(amount_inr) OVER (...).)
-- ----------------------------------------------------------------------------
WITH user_stats AS (
    SELECT
        txn_id,
        user_id,
        timestamp,
        amount_inr,
        is_fraud,
        AVG(amount_inr * 1.0) OVER (PARTITION BY user_id) AS user_avg,
        SQRT(
            AVG(amount_inr * 1.0 * amount_inr) OVER (PARTITION BY user_id)
            - AVG(amount_inr * 1.0) OVER (PARTITION BY user_id)
              * AVG(amount_inr * 1.0) OVER (PARTITION BY user_id)
        ) AS user_stddev
    FROM transactions
),
scored AS (
    SELECT
        *,
        CASE
            WHEN user_stddev > 0
            THEN (amount_inr - user_avg) / user_stddev
            ELSE 0
        END AS z_score
    FROM user_stats
)
SELECT
    txn_id,
    user_id,
    timestamp,
    amount_inr,
    ROUND(user_avg, 2)    AS user_avg_amount,
    ROUND(user_stddev, 2) AS user_stddev_amount,
    ROUND(z_score, 2)     AS z_score,
    is_fraud
FROM scored
WHERE z_score > 3
ORDER BY z_score DESC;

-- ----------------------------------------------------------------------------
-- Q5. Monthly trend — transaction volume, fraud count and fraud rate per month
-- with month-over-month change in fraud rate (LAG window function).
-- ----------------------------------------------------------------------------
WITH monthly AS (
    SELECT
        strftime('%Y-%m', timestamp) AS month,
        COUNT(*)                    AS total_txns,
        SUM(is_fraud)               AS fraud_txns
    FROM transactions
    GROUP BY 1
)
SELECT
    month,
    total_txns,
    fraud_txns,
    ROUND(100.0 * fraud_txns / total_txns, 2) AS fraud_rate_pct,
    ROUND(
        100.0 * fraud_txns / total_txns
        - LAG(100.0 * fraud_txns / total_txns) OVER (ORDER BY month),
        2
    ) AS mom_change_pp
FROM monthly
ORDER BY month;
