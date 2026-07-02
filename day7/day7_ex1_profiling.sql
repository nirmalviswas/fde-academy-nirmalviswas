-- ============================================================
-- EXERCISE 1 — TASK 1: Volume & Structure
-- ============================================================

-- Q1.1: Total row count
SELECT COUNT(*) AS total_rows FROM logistics_shipments;

-- Q1.2: Look at 10 real rows — never skip this step
SELECT * FROM logistics_shipments LIMIT 10;

-- Q1.3: Date range covered by the data
SELECT
    MIN(shipped_date) AS earliest_date,
    MAX(shipped_date) AS latest_date
FROM logistics_shipments;


-- ============================================================
-- EXERCISE 1 — TASK 2: Categorical Column Profiling
-- ============================================================

-- Q2.1: What are all the distinct carrier values?
SELECT DISTINCT carrier
FROM logistics_shipments;

-- Q2.2: How many shipments does each carrier have? (most to least)
SELECT carrier, COUNT(*) AS shipment_count
FROM logistics_shipments
GROUP BY carrier
ORDER BY COUNT(*) DESC;

-- Q2.3: What are all the distinct status values, and how common is each?
SELECT status, COUNT(*) AS status_count
FROM logistics_shipments
GROUP BY status
ORDER BY COUNT(*) DESC;

-- Q2.4: Which origin_city appears most frequently?
SELECT origin_city, COUNT(*) AS origin_count
FROM logistics_shipments
GROUP BY origin_city
ORDER BY COUNT(*) DESC
LIMIT 1;