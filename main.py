import json
import os
from fastapi import FastAPI

app = FastAPI()

# Always find the JSON file relative to this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data.json")

with open(DATA_FILE, "r") as f:
    groundwater_data = json.load(f)

@app.get("/stations")
def get_stations():
    return list(groundwater_data.keys())

@app.get("/station/{station_id}")
def get_station_data(station_id: str):
    return groundwater_data.get(station_id, [])
