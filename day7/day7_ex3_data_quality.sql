-- ============================================================
-- EXERCISE 3 — TASK 1: Duplicate & Referential Checks
-- ============================================================

-- Q1.1: Are there any duplicate shipment_id values?
-- (There should be ZERO since it's the primary key — but verify, don't assume)
SELECT shipment_id, COUNT(*) AS occurrences
FROM logistics_shipments
GROUP BY shipment_id
HAVING COUNT(*) > 1;

-- Q1.2: Are there any shipments where origin_city equals destination_city?
-- (A shipment FROM a city TO the same city is almost certainly a data error)
SELECT *
FROM logistics_shipments
WHERE origin_city = destination_city;


-- ============================================================
-- EXERCISE 3 — TASK 2: Impossible Numeric Values
-- ============================================================

-- Q2.1: Find shipments with negative delay_days (impossible — delay can't be negative)
SELECT * FROM logistics_shipments
WHERE delay_days < 0;

-- Q2.2: Find shipments with cost_usd of zero or negative
-- (a real shipment always costs something)
SELECT * FROM logistics_shipments
WHERE cost_usd <= 0;

-- Q2.3: Find shipments where delivered_date is BEFORE shipped_date (impossible — time travel)
SELECT * FROM logistics_shipments
WHERE delivered_date < shipped_date;

-- Q2.4: Count how many rows are affected by EACH of the above issues
SELECT
    SUM(CASE WHEN delay_days < 0 THEN 1 ELSE 0 END) AS negative_delay_count,
    SUM(CASE WHEN cost_usd <= 0 THEN 1 ELSE 0 END) AS zero_cost_count,
    SUM(CASE WHEN delivered_date < shipped_date THEN 1 ELSE 0 END) AS time_travel_count
FROM logistics_shipments;

-- ============================================================
-- EXERCISE 3 — TASK 3: Categorical & Text Quality Issues
-- ============================================================

-- Q3.1: Find any carrier values OUTSIDE the known valid set
SELECT DISTINCT carrier
FROM logistics_shipments
WHERE carrier NOT IN ('DHL', 'FEDEX', 'BLUEDART');

-- Q3.2: Find any status values outside the 4 expected categories
-- Valid set: 'delivered', 'in_transit', 'delayed', 'pending'
SELECT DISTINCT status
FROM logistics_shipments
WHERE status NOT IN ('delivered', 'in_transit', 'delayed', 'pending');

-- Q3.3: Find carrier values with inconsistent casing or extra whitespace
-- (This dataset was generated cleanly, but ALWAYS run this check on real client data)
SELECT DISTINCT carrier
FROM logistics_shipments
WHERE carrier != UPPER(TRIM(carrier));