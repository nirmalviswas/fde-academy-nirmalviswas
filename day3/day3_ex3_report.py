"""
AutoFinance Bank — Daily Shipment Operations Report
FDE Academy Day 3 Exercise 3

Usage:
    python day3_ex3_report.py

Outputs:
    - Console: formatted KPI report
    - shipments_summary.csv: per-carrier aggregated KPIs
    - route_report.csv: top routes by volume
"""

import pandas as pd
from pathlib import Path
from datetime import date

INPUT_FILE = "shipments_clean.csv"
SUMMARY_CSV = "shipments_summary.csv"
ROUTES_CSV = "route_report.csv"


def compute_carrier_kpis(df: pd.DataFrame) -> pd.DataFrame:
    """Compute per-carrier KPIs from the cleaned shipments DataFrame."""

    kpis = (
        df.groupby("carrier")
        .agg(
            total_shipments=("shipment_id", "count"),
            delivered=("status", lambda x: (x == "delivered").sum()),
            in_transit=("status", lambda x: (x == "in_transit").sum()),
            avg_delay_days=("delay_days", "mean"),
            max_delay_days=("delay_days", "max"),
            total_revenue=("cost_usd", "sum"),
            avg_cost_per_ship=("cost_usd", "mean"),
        )
        .reset_index()
    )

    def otif(group: pd.DataFrame) -> float:
        on_time = ((group["status"] == "delivered") & (group["delay_days"] == 0)).sum()
        return round(on_time / len(group) * 100, 1)

    otif_series = df.groupby("carrier").apply(otif).reset_index()
    otif_series.columns = ["carrier", "otif_pct"]

    kpis = kpis.merge(otif_series, on="carrier")
    kpis["avg_delay_days"] = kpis["avg_delay_days"].round(1)
    kpis["total_revenue"] = kpis["total_revenue"].round(2)
    kpis["avg_cost_per_ship"] = kpis["avg_cost_per_ship"].round(2)
    kpis["max_delay_days"] = kpis["max_delay_days"].astype(int)

    return kpis.sort_values("total_shipments", ascending=False)


def compute_route_report(df: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    """Compute a route-level report grouped by (origin, destination) pair."""

    df = df.copy()
    df["route"] = df["origin"] + " -> " + df["destination"]

    route_stats = (
        df.groupby("route")
        .agg(
            shipment_count=("shipment_id", "count"),
            avg_delay_days=("delay_days", "mean"),
            total_revenue=("cost_usd", "sum"),
        )
        .reset_index()
    )

    most_used = (
        df.groupby(["route", "carrier"])
        .size()
        .reset_index(name="cnt")
        .sort_values("cnt", ascending=False)
        .drop_duplicates(subset="route")[["route", "carrier"]]
        .rename(columns={"carrier": "most_used_carrier"})
    )

    route_stats = route_stats.merge(most_used, on="route")
    route_stats["avg_delay_days"] = route_stats["avg_delay_days"].round(1)
    route_stats["total_revenue"] = route_stats["total_revenue"].round(2)

    return route_stats.sort_values("shipment_count", ascending=False).head(top_n)


def print_console_report(
    df: pd.DataFrame,
    carrier_kpis: pd.DataFrame,
    route_report: pd.DataFrame,
) -> None:
    """Print a formatted operations report to the console."""

    today = date.today().isoformat()
    total_rev = df["cost_usd"].sum()
    overall_otif = round(
        ((df["status"] == "delivered") & (df["delay_days"] == 0)).sum() / len(df) * 100,
        1,
    )
    avg_delay = round(df["delay_days"].mean(), 1)

    print(f"\n=== AutoFinance Bank — Daily Shipment Report [{today}] ===")
    print(
        f"Total Shipments: {len(df)} | "
        f"Total Revenue: ${total_rev:,.2f} | "
        f"Overall OTIF: {overall_otif}% | "
        f"Avg Delay: {avg_delay} days"
    )

    print("\n=== Carrier KPIs ===")
    print(
        f"{'Carrier':<10} {'Shipments':>9} {'Delivered':>9} {'OTIF%':>6} {'Avg Delay':>10} {'Revenue':>10}"
    )
    for _, row in carrier_kpis.iterrows():
        print(
            f"{row['carrier']:<10} "
            f"{int(row['total_shipments']):>9} "
            f"{int(row['delivered']):>9} "
            f"{row['otif_pct']:>5.1f}% "
            f"{row['avg_delay_days']:>9.1f}d "
            f"${row['total_revenue']:>9,.2f}"
        )

    print("\n=== Top Routes ===")
    print(f"{'Route':<30} {'Count':>5} {'Avg Delay':>10} {'Revenue':>10}")
    for _, row in route_report.iterrows():
        print(
            f"{row['route']:<30} "
            f"{int(row['shipment_count']):>5} "
            f"{row['avg_delay_days']:>9.1f}d "
            f"${row['total_revenue']:>9,.2f}"
        )

    flagged = df[df["delay_days"] > 3]
    if not flagged.empty:
        print("\n⚠️  Flagged Shipments (delay > 3 days):")
        for _, row in flagged.iterrows():
            print(
                f"  {row['shipment_id']} {row['carrier']} "
                f"{row['status']} delay={int(row['delay_days'])} "
                f"cost=${row['cost_usd']:.2f}"
            )


def main() -> None:
    """Run the full report generation pipeline."""
    if not Path(INPUT_FILE).exists():
        print(f"ERROR: Input file not found: {INPUT_FILE}")
        return

    df = pd.read_csv(INPUT_FILE)

    required_cols = {"shipment_id", "carrier", "status", "delay_days", "cost_usd"}
    missing = required_cols - set(df.columns)
    if missing:
        print(f"ERROR: Missing required columns: {missing}")
        return

    if len(df) == 0:
        print("ERROR: Input file contains no data rows")
        return

    carrier_kpis = compute_carrier_kpis(df)
    route_report = compute_route_report(df, top_n=5)

    carrier_kpis.to_csv(SUMMARY_CSV, index=False)
    route_report.to_csv(ROUTES_CSV, index=False)

    print_console_report(df, carrier_kpis, route_report)
    print(f"\nSaved: {SUMMARY_CSV} | {ROUTES_CSV}")


if __name__ == "__main__":
    main()
