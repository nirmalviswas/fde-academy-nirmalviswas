-- ============================================================
-- EXERCISE 3: Top-3 Underperforming Regions — Multi-Join
-- ============================================================

-- TASK 1: JOIN and aggregate by region (unfiltered baseline — look before filtering)
SELECT
    r.region_name,
    COUNT(*)          AS shipment_count,
    AVG(s.delay_days) AS avg_delay,
    SUM(s.cost_usd)   AS total_cost
FROM logistics_shipments s
INNER JOIN regions r ON s.destination_region_id = r.region_id
GROUP BY r.region_name
ORDER BY avg_delay DESC;

-- ============================================================
-- TASK 2: Add HAVING to exclude low-volume regions (>= 500 shipments)
-- ============================================================
SELECT
    r.region_name,
    COUNT(*)          AS shipment_count,
    AVG(s.delay_days) AS avg_delay,
    SUM(s.cost_usd)   AS total_cost
FROM logistics_shipments s
INNER JOIN regions r ON s.destination_region_id = r.region_id
GROUP BY r.region_name
HAVING COUNT(*) >= 500
ORDER BY avg_delay DESC;

-- ============================================================
-- TASK 3: Select exactly top 3 using ROW_NUMBER
-- ============================================================
WITH region_stats AS (
    SELECT
        r.region_name,
        COUNT(*)          AS shipment_count,
        AVG(s.delay_days) AS avg_delay,
        SUM(s.cost_usd)   AS total_cost
    FROM logistics_shipments s
    INNER JOIN regions r ON s.destination_region_id = r.region_id
    GROUP BY r.region_name
    HAVING COUNT(*) >= 500
),
region_ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (ORDER BY avg_delay DESC) AS underperformance_rank
    FROM region_stats
)
SELECT
    region_name,
    shipment_count,
    ROUND(avg_delay::numeric, 2)  AS avg_delay,
    ROUND(total_cost::numeric, 2) AS total_cost
FROM region_ranked
WHERE underperformance_rank <= 3
ORDER BY underperformance_rank;