import pandas as pd
from pathlib import Path

VALID_STATUSES = {"in_transit", "delivered", "pending", "exception"}
VALID_CARRIERS = {"DHL", "FEDEX", "BLUEDART"}


def load_shipments(file_path: str) -> list[dict]:
    """Load a shipments CSV file, drop completely empty rows."""
    df = pd.read_csv(file_path, encoding="utf-8", dtype=str)
    df = df.dropna(how="all")
    return df.to_dict(orient="records")


def normalise_row(row: dict) -> dict:
    """Normalise string fields in a single row dict."""
    row = row.copy()

    sid = row.get("shipment_id")
    row["shipment_id"] = (
        str(sid).strip() if sid and str(sid).strip() not in ("", "nan") else None
    )

    carrier = row.get("carrier")
    row["carrier"] = (
        str(carrier).strip().upper()
        if carrier and str(carrier).strip() not in ("", "nan")
        else None
    )

    status = row.get("status")
    row["status"] = (
        str(status).strip().lower()
        if status and str(status).strip() not in ("", "nan")
        else None
    )

    origin = row.get("origin")
    row["origin"] = (
        str(origin).strip().title()
        if origin and str(origin).strip() not in ("", "nan")
        else None
    )

    dest = row.get("destination")
    row["destination"] = (
        str(dest).strip().title()
        if dest and str(dest).strip() not in ("", "nan")
        else None
    )

    try:
        row["delay_days"] = int(float(str(row.get("delay_days", "")).strip()))
    except (ValueError, TypeError):
        row["delay_days"] = None

    try:
        row["cost_usd"] = float(str(row.get("cost_usd", "")).strip())
    except (ValueError, TypeError):
        row["cost_usd"] = None

    return row


def validate_row(row: dict) -> list[str]:
    """Validate a normalised row. Returns list of error strings."""
    errors = []

    if not row.get("shipment_id"):
        errors.append("shipment_id must not be empty")

    if not row.get("carrier") or row["carrier"] not in VALID_CARRIERS:
        errors.append("carrier must be in VALID_CARRIERS")

    if not row.get("status") or row["status"] not in VALID_STATUSES:
        errors.append("status must be in VALID_STATUSES")

    if row.get("delay_days") is None or row["delay_days"] < 0:
        errors.append("delay_days must be >= 0")

    if row.get("cost_usd") is None or row["cost_usd"] <= 0:
        errors.append("cost_usd must not be None and must be > 0")

    return errors


def clean_shipments(
    input_path: str,
    clean_output_path: str,
    rejected_output_path: str,
) -> dict:
    """Run the full cleaning pipeline."""
    records = load_shipments(input_path)
    normalised = [normalise_row(r) for r in records]

    clean_rows = []
    rejected_rows = []

    for row in normalised:
        errors = validate_row(row)
        if errors:
            row["rejection_reasons"] = "; ".join(errors)
            rejected_rows.append(row)
        else:
            clean_rows.append(row)

    if clean_rows:
        pd.DataFrame(clean_rows).to_csv(clean_output_path, index=False)
    if rejected_rows:
        pd.DataFrame(rejected_rows).to_csv(rejected_output_path, index=False)

    all_reasons: list[str] = []
    for row in rejected_rows:
        for reason in row["rejection_reasons"].split("; "):
            reason = reason.strip()
            if reason and reason not in all_reasons:
                all_reasons.append(reason)

    total = len(normalised)
    rejected_count = len(rejected_rows)

    return {
        "total_input": total,
        "clean_count": len(clean_rows),
        "rejected_count": rejected_count,
        "rejection_rate_pct": round(rejected_count / total * 100, 1) if total else 0.0,
        "rejection_reasons": all_reasons,
    }


if __name__ == "__main__":
    summary = clean_shipments(
        input_path="shipments_raw.csv",
        clean_output_path="shipments_clean.csv",
        rejected_output_path="shipments_rejected.csv",
    )

    print("\n=== Data Quality Report ===")
    for key, value in summary.items():
        print(f"  {key:<25} {value}")
