-- ============================================================
-- EXERCISE 2: Supplier Performance Ranking via CTE Chain
-- ============================================================

-- TASK 1: CTE 1 — Raw per-carrier aggregates with LEFT JOIN
-- LEFT JOIN ensures DTDC (zero shipments) still appears in results
WITH carrier_raw_stats AS (
    SELECT
        c.carrier_code,
        c.carrier_name,
        c.sla_days,
        COUNT(s.shipment_id)    AS total_shipments,  -- COUNT(col) not COUNT(*) — returns 0 for DTDC
        AVG(s.delay_days)       AS avg_delay,
        SUM(s.cost_usd)         AS total_revenue,
        SUM(CASE WHEN s.status = 'delivered' AND s.delay_days = 0
                 THEN 1 ELSE 0 END) AS on_time_count
    FROM carriers c
    LEFT JOIN logistics_shipments s ON c.carrier_code = s.carrier
    GROUP BY c.carrier_code, c.carrier_name, c.sla_days
)
SELECT * FROM carrier_raw_stats;

-- ============================================================
-- TASK 2: CTE 2 — Compute OTIF% safely (avoid divide-by-zero)
-- ============================================================
WITH carrier_raw_stats AS (
    SELECT
        c.carrier_code,
        c.carrier_name,
        c.sla_days,
        COUNT(s.shipment_id)    AS total_shipments,
        AVG(s.delay_days)       AS avg_delay,
        SUM(s.cost_usd)         AS total_revenue,
        SUM(CASE WHEN s.status = 'delivered' AND s.delay_days = 0
                 THEN 1 ELSE 0 END) AS on_time_count
    FROM carriers c
    LEFT JOIN logistics_shipments s ON c.carrier_code = s.carrier
    GROUP BY c.carrier_code, c.carrier_name, c.sla_days
),
carrier_otif AS (
    SELECT
        *,
        CASE WHEN total_shipments = 0 THEN NULL
             ELSE ROUND(100.0 * on_time_count / total_shipments, 1)
        END AS otif_pct
    FROM carrier_raw_stats
)
SELECT * FROM carrier_otif;

-- ============================================================
-- TASK 3: CTE 3 — Rank across three dimensions
-- ============================================================
WITH carrier_raw_stats AS (
    SELECT
        c.carrier_code,
        c.carrier_name,
        c.sla_days,
        COUNT(s.shipment_id)    AS total_shipments,
        AVG(s.delay_days)       AS avg_delay,
        SUM(s.cost_usd)         AS total_revenue,
        SUM(CASE WHEN s.status = 'delivered' AND s.delay_days = 0
                 THEN 1 ELSE 0 END) AS on_time_count
    FROM carriers c
    LEFT JOIN logistics_shipments s ON c.carrier_code = s.carrier
    GROUP BY c.carrier_code, c.carrier_name, c.sla_days
),
carrier_otif AS (
    SELECT
        *,
        CASE WHEN total_shipments = 0 THEN NULL
             ELSE ROUND(100.0 * on_time_count / total_shipments, 1)
        END AS otif_pct
    FROM carrier_raw_stats
),
carrier_ranked AS (
    SELECT
        *,
        RANK() OVER (ORDER BY otif_pct DESC NULLS LAST)   AS otif_rank,
        RANK() OVER (ORDER BY avg_delay ASC NULLS LAST)   AS delay_rank,
        RANK() OVER (ORDER BY total_revenue DESC NULLS LAST) AS revenue_rank
    FROM carrier_otif
)
SELECT
    carrier_name,
    total_shipments,
    ROUND(otif_pct::numeric, 1)     AS otif_pct,
    otif_rank,
    ROUND(avg_delay::numeric, 2)    AS avg_delay,
    delay_rank,
    ROUND(total_revenue::numeric, 2) AS total_revenue,
    revenue_rank
FROM carrier_ranked
ORDER BY otif_rank;