-- ============================================================
-- EXERCISE 2: Business KPI Queries
-- ============================================================

-- Q1: How many total shipments are currently delayed?
SELECT COUNT(*) AS delayed_count
FROM logistics_shipments
WHERE status = 'delayed';

-- Q2: Total shipment cost by carrier
SELECT carrier, SUM(cost_usd) AS total_cost
FROM logistics_shipments
GROUP BY carrier
ORDER BY total_cost DESC;

-- Q3: Carrier with highest average delay
SELECT carrier, AVG(delay_days) AS avg_delay
FROM logistics_shipments
GROUP BY carrier
ORDER BY avg_delay DESC
LIMIT 1;

-- Q4: Top 5 most expensive shipments
SELECT shipment_id, carrier, cost_usd
FROM logistics_shipments
ORDER BY cost_usd DESC
LIMIT 5;

-- Q5: OTIF percentage (on-time-in-full)
SELECT
    ROUND(
        100.0 * SUM(CASE WHEN status = 'delivered' AND delay_days = 0 THEN 1 ELSE 0 END)
        / COUNT(*),
        1
    ) AS otif_pct
FROM logistics_shipments;

-- Q6: Highest-volume route
SELECT origin_city, destination_city, COUNT(*) AS shipment_count
FROM logistics_shipments
GROUP BY origin_city, destination_city
ORDER BY shipment_count DESC
LIMIT 1;

-- Q7: Carriers averaging over $300
SELECT carrier, AVG(cost_usd) AS avg_cost
FROM logistics_shipments
GROUP BY carrier
HAVING AVG(cost_usd) > 300;

-- Q8: Shipments per status, ranked
SELECT status, COUNT(*) AS status_count
FROM logistics_shipments
GROUP BY status
ORDER BY status_count DESC;

-- Q9: Total weight shipped by DHL
SELECT SUM(weight_kg) AS dhl_total_weight
FROM logistics_shipments
WHERE carrier = 'DHL';

-- Q10: Top 3 most-delayed destination cities
SELECT destination_city, COUNT(*) AS delayed_count
FROM logistics_shipments
WHERE status = 'delayed'
GROUP BY destination_city
ORDER BY delayed_count DESC
LIMIT 3;
