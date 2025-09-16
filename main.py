import json
import os
import statistics
import calendar

from fastapi import FastAPI, Query
from datetime import datetime, timedelta

app = FastAPI()

# Load mock data.json
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "mock_groundwater_data.json")  # <-- use new dataset
with open(DATA_FILE, "r") as f:
    groundwater_data = json.load(f)


def summarize(data):
    """Return summary stats for water_level."""
    if not data:
        return {}
    levels = [d["water_level"] for d in data]
    return {
        "count": len(levels),
        "min": min(levels),
        "max": max(levels),
        "avg": round(statistics.mean(levels), 2),
    }


@app.get("/states")
def get_states():
    """Return list of all unique states."""
    states = {v["state"] for v in groundwater_data.values()}
    return sorted(states)


@app.get("/districts/{state}")
def get_districts(state: str):
    """Return all districts for a given state."""
    districts = {v["district"] for v in groundwater_data.values() if v["state"].lower() == state.lower()}
    return sorted(districts)


@app.get("/stations")
def get_stations(state: str = None, district: str = None):
    """
    Return station IDs.
    Optional filters: by state, by district.
    """
    stations = []
    for station_id, v in groundwater_data.items():
        if state and v["state"].lower() != state.lower():
            continue
        if district and v["district"].lower() != district.lower():
            continue
        stations.append(station_id)
    return stations


@app.get("/station/{station_id}")
def get_station_data(
    station_id: str,
    filter: str = Query(
        None,
        description="Filter type: latest, day, month, season, custom",
    ),
    start: str = Query(None, description="Custom start timestamp (ISO format)"),
    end: str = Query(None, description="Custom end timestamp (ISO format)"),
    year: int = Query(None, ge=1, le=9999, description="Calendar year for month filter"),
    month: int = Query(None, ge=1, le=12, description="Calendar month (1-12) for month filter"),
):
    """Return station data with filters and summary."""
    station = groundwater_data.get(station_id)
    if not station:
        return {"station_id": station_id, "data": [], "summary": {}}

    data = station["data"]

    # Convert timestamps to datetime for filtering
    for d in data:
        d["dt"] = datetime.fromisoformat(d["timestamp"])
    now = max(d["dt"] for d in data)

    # Apply filters
    if filter == "latest":
        filtered = [max(data, key=lambda d: d["dt"])]
    elif filter == "day":
        filtered = [d for d in data if d["dt"] >= now - timedelta(days=1)]
    elif filter == "month" and year and month:
        first_day = datetime(year, month, 1)
        last_day = datetime(year, month, calendar.monthrange(year, month)[1], 23, 59, 59)
        filtered = [d for d in data if first_day <= d["dt"] <= last_day]
    elif filter == "month":
        filtered = [d for d in data if d["dt"] >= now - timedelta(days=30)]
    elif filter == "season":
        filtered = [d for d in data if d["dt"] >= now - timedelta(days=90)]
    elif filter == "custom" and start and end:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
        filtered = [d for d in data if start_dt <= d["dt"] <= end_dt]
    else:
        filtered = data

    # Remove helper field before returning
    for d in filtered:
        d.pop("dt", None)

    return {
        "station_id": station_id,
        "state": station["state"],
        "district": station["district"],
        "filter": filter,
        "summary": summarize(filtered),
        "data": filtered,
    }
