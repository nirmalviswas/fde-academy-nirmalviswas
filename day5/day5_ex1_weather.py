from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional

# ============================================================
# TASK 1: Mock Weather API & Response Data
# ============================================================

MOCK_API_RESPONSES: dict[str, dict] = {
    "Mumbai": {
        "location": {"name": "Mumbai", "region": "Maharashtra", "country": "India"},
        "current": {
            "temp_c": 31.0,
            "humidity": 70,
            "wind_kph": 14.4,
            "condition": {"text": "Partly cloudy"},
            "air_quality": {"pm2_5": 42.1},
        },
        "forecast": {
            "forecastday": [
                {
                    "date": "2024-01-21",
                    "day": {
                        "maxtemp_c": 32.0,
                        "mintemp_c": 24.0,
                        "condition": {"text": "Sunny"},
                    },
                }
            ]
        },
    },
    "Chennai": {
        "location": {"name": "Chennai", "region": "Tamil Nadu", "country": "India"},
        "current": {
            "temp_c": 29.5,
            "humidity": 78,
            "wind_kph": 9.0,
            "condition": {"text": "Humid and partly cloudy"},
            # NOTE: air_quality is missing entirely for this city
        },
        "forecast": {
            "forecastday": [
                {
                    "date": "2024-01-21",
                    "day": {
                        "maxtemp_c": 30.0,
                        "mintemp_c": 25.0,
                        "condition": {"text": "Patchy rain possible"},
                    },
                }
            ]
        },
    },
    "Bengaluru": {
        "location": {"name": "Bengaluru", "region": "Karnataka", "country": "India"},
        "current": {
            "temp_c": 24.0,
            "humidity": 55,
            "wind_kph": 11.0,
            "condition": {"text": "Clear"},
            "air_quality": {"pm2_5": 18.3},
        },
        "forecast": {"forecastday": []},  # NOTE: empty forecast list
    },
    "Delhi": {
        "location": {"name": "Delhi", "country": "India"},  # NOTE: region missing
        "current": {
            "temp_c": 18.0,
            "humidity": 40,
            "wind_kph": 6.0,
            "condition": {"text": "Foggy"},
            "air_quality": {"pm2_5": 95.4},
        },
        "forecast": {
            "forecastday": [
                {
                    "date": "2024-01-21",
                    "day": {
                        "maxtemp_c": 20.0,
                        "mintemp_c": 9.0,
                        "condition": {"text": "Sunny"},
                    },
                }
            ]
        },
    },
    "Hyderabad": {
        "location": {"name": "Hyderabad", "region": "Telangana", "country": "India"},
        "current": {
            "temp_c": 27.0,
            "humidity": 60,
            "wind_kph": 10.0,
            "condition": {"text": "Sunny"},
            "air_quality": {"pm2_5": 30.0},
        },
        "forecast": {
            "forecastday": [
                {
                    "date": "2024-01-21",
                    "day": {
                        "maxtemp_c": 29.0,
                        "mintemp_c": 19.0,
                        "condition": {"text": "Sunny"},
                    },
                }
            ]
        },
    },
}


def mock_get_weather(city: str) -> dict:
    """Simulates an HTTP GET call to a weather API for the given city."""
    if city not in MOCK_API_RESPONSES:
        raise ValueError(f"Unknown city: {city!r}")
    return MOCK_API_RESPONSES[city]


# ============================================================
# TASK 2A: Pydantic output schema
# ============================================================


class DashboardWeatherRecord(BaseModel):
    """Validated, flat weather record ready for the operations dashboard."""

    city: str
    region: Optional[str] = None
    temp_c: float = Field(..., ge=-90, le=60)
    condition: str
    humidity_pct: int = Field(..., ge=0, le=100)
    wind_kph: float = Field(..., ge=0)
    pm2_5: Optional[float] = None
    tomorrow_max_c: Optional[float] = None
    tomorrow_min_c: Optional[float] = None
    tomorrow_outlook: Optional[str] = None


# ============================================================
# TASK 2B: Transform function
# ============================================================


def transform_weather_to_dashboard(raw: dict) -> DashboardWeatherRecord:
    """
    Flatten a nested weather API response into a DashboardWeatherRecord.

    Must handle gracefully:
    - Missing 'region' in location (use None)
    - Missing 'air_quality' block entirely (pm2_5 = None)
    - Empty 'forecastday' list (tomorrow_* fields = None)
    """
    location = raw.get("location", {})
    current = raw.get("current", {})
    air = current.get("air_quality", {})

    forecast_days = raw.get("forecast", {}).get("forecastday", [])
    tomorrow = forecast_days[0] if forecast_days else {}
    tomorrow_day = tomorrow.get("day", {})

    flat = {
        "city": location.get("name", "Unknown"),
        "region": location.get("region"),
        "temp_c": current.get("temp_c"),
        "condition": current.get("condition", {}).get("text", "Unknown"),
        "humidity_pct": current.get("humidity"),
        "wind_kph": current.get("wind_kph"),
        "pm2_5": air.get("pm2_5"),
        "tomorrow_max_c": tomorrow_day.get("maxtemp_c"),
        "tomorrow_min_c": tomorrow_day.get("mintemp_c"),
        "tomorrow_outlook": tomorrow_day.get("condition", {}).get("text"),
    }

    return DashboardWeatherRecord(**flat)


# ============================================================
# TASK 2C: Batch transform for all hub cities
# ============================================================


def build_dashboard_panel(cities: list[str]) -> list[DashboardWeatherRecord]:
    """
    Fetch and transform weather for multiple cities.
    If a city fails (unknown city, API error), log it and skip.
    """
    panel: list[DashboardWeatherRecord] = []
    for city in cities:
        try:
            raw = mock_get_weather(city)
            record = transform_weather_to_dashboard(raw)
            panel.append(record)
        except Exception as e:
            print(f"Skipping {city}: {e}")
    return panel


# ============================================================
# TASK 3: Main script
# ============================================================

if __name__ == "__main__":
    hub_cities = ["Mumbai", "Chennai", "Bengaluru", "Delhi", "Hyderabad", "Pune"]
    # Note: 'Pune' is NOT in MOCK_API_RESPONSES — tests your error handling

    panel = build_dashboard_panel(hub_cities)

    print(f"Dashboard panel built: {len(panel)} of {len(hub_cities)} cities succeeded")
    print()

    for record in panel:
        print(
            f"{record.city:<12} {record.temp_c:>5.1f}C {record.condition:<25} "
            f"PM2.5={record.pm2_5}"
        )
        if record.tomorrow_max_c is not None:
            print(
                f"  Tomorrow: {record.tomorrow_min_c}-{record.tomorrow_max_c}C, "
                f"{record.tomorrow_outlook}"
            )
        else:
            print("  Tomorrow: No forecast data available")
        print()
