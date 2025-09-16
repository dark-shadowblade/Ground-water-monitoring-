import json
import os
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, Query, HTTPException
from datetime import datetime, timedelta
import statistics

app = FastAPI(title="Groundwater API")

# ---- Load data.json (required) ----
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data.json")

if not os.path.exists(DATA_FILE):
    raise FileNotFoundError(f"data.json not found at {DATA_FILE}")

with open(DATA_FILE, "r") as f:
    groundwater_data: Dict[str, List[Dict[str, Any]]] = json.load(f)

# ---- Utilities ----
def summarize(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Return summary stats for water_level."""
    if not data:
        return {}
    levels = [d["water_level"] for d in data if "water_level" in d]
    if not levels:
        return {}
    return {
        "count": len(levels),
        "min": min(levels),
        "max": max(levels),
        "avg": round(statistics.mean(levels), 2),
    }

def parse_station_data(station: List[Dict[str, Any]]) -> List[tuple]:
    """Return list of (record, datetime) without mutating original dicts."""
    parsed = []
    for d in station:
        ts = d.get("timestamp")
        if ts is None:
            continue
        try:
            dt = datetime.fromisoformat(ts)
        except Exception:
            # Skip malformed timestamps
            continue
        parsed.append((d, dt))
    return parsed

# ---- Endpoints ----
@app.get("/health")
def health():
    return {"ok": True}

@app.get("/stations")
def get_stations() -> List[str]:
    return list(groundwater_data.keys())

@app.get("/station/{station_id}")
def get_station_data(
    station_id: str,
    filter: Optional[str] = Query(
        None,
        description="Filter type: latest, day, month, season, custom",
    ),
    start: Optional[str] = Query(None, description="Custom start timestamp (ISO format)"),
    end: Optional[str] = Query(None, description="Custom end timestamp (ISO format)"),
):
    """Return station data with filters and computed summary."""
    data = groundwater_data.get(station_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Unknown station_id: {station_id}")

    parsed = parse_station_data(data)
    if not parsed:
        return {"station_id": station_id, "filter": filter, "summary": {}, "data": []}

    now = max(dt for _, dt in parsed)

    if filter == "latest":
        filtered = [max(parsed, key=lambda x: x[1])]
    elif filter == "day":
        cutoff = now - timedelta(days=1)
        filtered = [d for d, dt in parsed if dt >= cutoff]
    elif filter == "month":
        cutoff = now - timedelta(days=30)
        filtered = [d for d, dt in parsed if dt >= cutoff]
    elif filter == "season":
        # One season = last 90 days (adjust if needed)
        cutoff = now - timedelta(days=90)
        filtered = [d for d, dt in parsed if dt >= cutoff]
    elif filter == "custom":
        if not start or not end:
            raise HTTPException(status_code=400, detail="start and end are required for custom filter")
        try:
            start_dt = datetime.fromisoformat(start)
            end_dt = datetime.fromisoformat(end)
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="start/end must be ISO timestamps like 2023-03-15T18:00:00"
            )
        if start_dt > end_dt:
            raise HTTPException(status_code=400, detail="start must be <= end")
        filtered = [d for d, dt in parsed if start_dt <= dt <= end_dt]
    else:
        # No filter or unknown filter -> return all
        filtered = [d for d, _ in parsed]

    return {
        "station_id": station_id,
        "filter": filter,
        "summary": summarize(filtered),
        "data": filtered,
    }
    
