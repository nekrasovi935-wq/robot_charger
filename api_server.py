import uvicorn
from fastapi import FastAPI
import math

app = FastAPI(title="ArUco Docking API")

api_data = {
    "status": "starting",
    "marker": None,
    "robot_command": None
}

@app.get("/health")
def health():
    return {"ok": True, "status": api_data["status"], "last_error": None}

@app.get("/api/v1/detections")
def get_detections():
    return api_data

def update_state(pose, state_name, v, w):
    api_data["status"] = "running"
    if pose is None:
        api_data["marker"] = None
        api_data["robot_command"] = None
    else:
        bearing_deg = math.degrees(pose.bearing)
        direction = "RIGHT" if bearing_deg > 0 else "LEFT"
        
        api_data["marker"] = {
            "id": int(pose.payload),
            "distance_m": round(pose.distance, 2),
            "bearing_deg": round(bearing_deg, 1),
            "direction": direction,
            "x_m": round(pose.x, 2),
            "z_m": round(pose.z, 2)
        }
        api_data["robot_command"] = {
            "linear_x": round(v, 2),
            "angular_z": round(w, 2)
        }

def run_server():
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")