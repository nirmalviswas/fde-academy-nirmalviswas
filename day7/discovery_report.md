# Data Discovery Report — `logistics_shipments`
**TechStar Group | FDE Academy | Day 7**

---

## Exercise 1: Data Profile

### Volume & Structure
- **Total rows:** 100,000
- **Date range:** 2024-01-01 to 2024-06-29
- Sample rows (Q1.2) confirm realistic logistics data: valid carrier names, city names, and statuses.

### Categorical Profile
- **Carriers (3 distinct):** DHL (37,647 / ~37.6%), FEDEX (37,143 / ~37.1%), BLUEDART (25,210 / ~25.2%)
- **Status categories (4 distinct):** delivered, in_transit, delayed, pending (roughly even distribution — to be confirmed in Exercise 2)
- **Origin cities (6 distinct):** Mumbai, Chennai, Pune, Delhi, Hyderabad, Bangalore

### NULL Audit
| total_rows | null_carrier | null_status | null_cost | null_delay | null_delivered_date |
|---|---|---|---|---|---|
| 100,000 | 0 | 0 | 0 | 0 | 0 |

**Zero NULLs across all business-critical columns.**

### Numeric Range Check
| Column | Min | Max | Avg |
|---|---|---|---|
| cost_usd | 0.00 | 499.99 | 270.18 |
| delay_days | -1 | (pending) | (pending) |
| weight_kg | (pending) | (pending) | (pending) |

**⚠️ Anomalies found despite zero NULLs:**
- `min_cost = 0.00` — a real shipment should never cost $0 (~2% of rows, per injection rate)
- `min_delay = -1` — delay cannot be negative (~3% of rows, per injection rate)

---

## Reflection Answers (Exercise 1)

**Q: Are the negative delay / zero cost values NULLs? Why might an FDE consider them worse than NULLs?**

No — they are fully populated, valid-looking numeric values that pass undetected through any NULL check. This makes them more dangerous than NULLs: a NULL openly signals missing data and gets handled explicitly, while a disguised bad value (e.g., `cost_usd = 0`) silently flows into downstream calculations — corrupting averages, sums, and KPIs — without ever raising a flag.

**Q: Would the NULL audit catch `carrier = ''`? What additional query would catch it?**

No. `COUNT(*) - COUNT(carrier)` only detects true SQL NULLs; an empty string is a non-NULL value. Additional check:
```sql
SELECT COUNT(*) AS empty_or_whitespace_carrier
FROM logistics_shipments
WHERE TRIM(carrier) = '';
```

**Q: Five-line discovery summary for the engagement lead:**

> The `logistics_shipments` table contains exactly 100,000 rows spanning shipped dates from 2024-01-01 to 2024-06-29, with three carriers (DHL, FEDEX, BLUEDART) and four status categories. All business-critical columns are 100% populated with zero NULLs. However, this NULL-clean appearance is misleading: a numeric range check reveals approximately 3% of rows have an impossible negative `delay_days` value and approximately 2% have a `cost_usd` of exactly $0.00, neither of which is physically valid for a real shipment. These issues require explicit anomaly-detection rules — not just NULL checks — before this data can safely feed any downstream pipeline or dashboard.

---

## Exercise 2: Business Queries

All 10 KPI queries verified working correctly against the 100K-row dataset.

**Key results:**
- Q5 (OTIF%): 0.8% — low, but mathematically correct given independent random generation of `status` and `delay_days` (delivered_count=16,723, zero_delay_count=4,887, otif_count=821 → 821/100,000 = 0.82%)
- Q7 (carriers averaging > $300): **0 rows** — correctly returns empty, since cost is generated independently of carrier and no carrier's average exceeds ~$270 overall average

### Reflection Answers (Exercise 2)

**Q: Key conceptual difference between WHERE-only and HAVING queries?**

`WHERE` filters individual rows before grouping/aggregation; `HAVING` filters grouped results after aggregation, since it needs to reference aggregate values (e.g. `AVG()`, `COUNT()`) that don't exist until rows have been collapsed into groups.

**Q: How would Q5 change to show OTIF% per carrier?**

```sql
SELECT
    carrier,
    ROUND(
        100.0 * SUM(CASE WHEN status = 'delivered' AND delay_days = 0 THEN 1 ELSE 0 END)
        / COUNT(*),
        1
    ) AS otif_pct
FROM logistics_shipments
GROUP BY carrier
ORDER BY otif_pct DESC;
```

**Q: Which queries would become permanent dashboard tiles vs. one-off discovery questions?**

- **Permanent tiles:** Q1 (delayed count), Q2 (cost by carrier), Q3 (avg delay by carrier), Q5 (OTIF%), Q8 (status breakdown) — recurring KPIs worth tracking continuously.
- **One-off discovery:** Q4 (top 5 expensive shipments), Q6 (highest-volume route), Q9 (DHL weight total), Q10 (top 3 delayed destinations) — point-in-time answers, not continuous monitoring needs.


## Exercise 3: Data Quality Anomaly Detection
*(to be completed)*