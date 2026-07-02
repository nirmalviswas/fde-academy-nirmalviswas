-- ============================================================
-- EXERCISE 1: 30-Day Rolling Average Shipment Delay
-- ============================================================

-- TASK 1: Aggregate to one row per day
WITH daily_delays AS (
    SELECT
        shipped_date,
        AVG(delay_days) AS avg_delay_that_day,
        COUNT(*)        AS shipments_that_day
    FROM logistics_shipments
    GROUP BY shipped_date
)
SELECT * FROM daily_delays
ORDER BY shipped_date
LIMIT 10;

-- Verify: how many distinct days does the data cover?
SELECT COUNT(DISTINCT shipped_date) AS distinct_days
FROM logistics_shipments;

-- ============================================================
-- TASK 2: Apply the 30-day rolling window (RANGE-based)
-- ============================================================
WITH daily_delays AS (
    SELECT
        shipped_date,
        AVG(delay_days) AS avg_delay_that_day
    FROM logistics_shipments
    GROUP BY shipped_date
)
SELECT
    shipped_date,
    avg_delay_that_day,
    AVG(avg_delay_that_day) OVER (
        ORDER BY shipped_date
        RANGE BETWEEN INTERVAL '29 days' PRECEDING AND CURRENT ROW
    ) AS rolling_30day_avg
FROM daily_delays
ORDER BY shipped_date;

-- ============================================================
-- TASK 3: Compare ROWS vs RANGE behaviour side by side
-- ============================================================
WITH daily_delays AS (
    SELECT
        shipped_date,
        AVG(delay_days) AS avg_delay_that_day
    FROM logistics_shipments
    GROUP BY shipped_date
)
SELECT
    shipped_date,
    ROUND(avg_delay_that_day::numeric, 2)             AS avg_delay_that_day,
    ROUND(AVG(avg_delay_that_day) OVER (
        ORDER BY shipped_date
        RANGE BETWEEN INTERVAL '29 days' PRECEDING AND CURRENT ROW
    )::numeric, 2)                                     AS rolling_30_calendar_day,
    ROUND(AVG(avg_delay_that_day) OVER (
        ORDER BY shipped_date
        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    )::numeric, 2)                                     AS rolling_30_row
FROM daily_delays
ORDER BY shipped_date;