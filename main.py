from fastapi import FastAPI
import pandas as pd

app = FastAPI()

# Load dataset
df = pd.read_csv("fake_dwlr_data.csv")

@app.get("/")
def root():
    return {"message": "Groundwater Monitoring API running 🚰"}

@app.get("/stations")
def get_stations():
    return {"stations": df["Station_ID"].unique().tolist()}

@app.get("/station/{station_id}")
def get_station_data(station_id: str, limit: int = 100):
    data = df[df["Station_ID"] == station_id].tail(limit)
    return data.to_dict(orient="records")
