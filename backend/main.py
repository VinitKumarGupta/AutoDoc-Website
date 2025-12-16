import asyncio
import json
import random
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

# IMPORTANT: Import from the new robust_db
from robust_db import (
    add_stock,
    assign_vehicle,
    authenticate_dealer,
    authenticate_owner,
    get_dealer_snapshot,
    list_service_bookings,
    record_service_booking,
)

from agent_graph import agent_workflow
from predictive import predict_breakdown_risk
from alert_service import AlertTriggerService
from request_security import RequestSecurityMiddleware
from ueba_engine import analyze as ueba_analyze
from access_control import apply_access_control
from intelligent_chatbot import generate_ai_response
from fastapi import Depends, Request

app = FastAPI()

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)
SECURITY_LOGS: List[Dict[str, Any]] = []
app.add_middleware(RequestSecurityMiddleware, log_store=SECURITY_LOGS)

# --- MODELS ---
class LoginRequest(BaseModel):
    username: str
    password: str
    role: str # 'user' or 'dealer'

class AddStockRequest(BaseModel):
    dealer_id: str
    chassis_number: str
    model: str

class AssignRequest(BaseModel):
    dealer_id: str
    chassis_number: str
    target_username: str

class ServiceCenterRequest(BaseModel):
    location_lat: float
    location_lon: float

class ServiceRequest(BaseModel):
    chassis_number: str
    owner_name: str
    issue: str
    dealer_name: str
    location_lat: Optional[float] = None
    location_lon: Optional[float] = None
    center_id: Optional[str] = None

class ChatbotQuery(BaseModel):
    chassis_number: str
    question: str

# --- API ENDPOINTS ---

@app.post("/login")
async def login(req: LoginRequest):
    if req.role == "dealer":
        dealer = authenticate_dealer(req.username, req.password)
        if not dealer:
            raise HTTPException(401, "Invalid Dealer Login")
        return {"role": "dealer", "data": dealer}

    if req.role == "user":
        user = authenticate_owner(req.username, req.password)
        if not user:
            raise HTTPException(401, "Invalid User Login")
        return {"role": "user", "data": user}

    raise HTTPException(400, "Unknown Role")

@app.post("/dealer/add-stock")
async def api_add_stock(req: AddStockRequest):
    success = add_stock(req.dealer_id, req.chassis_number, req.model)
    if not success:
        raise HTTPException(400, "Failed to add stock (Duplicate VIN?)")
    latest = get_dealer_snapshot(req.dealer_id)
    if not latest:
        raise HTTPException(404, "Dealer not found")
    return latest["inventory"]

@app.post("/dealer/assign")
async def api_assign(req: AssignRequest):
    success, msg = assign_vehicle(req.dealer_id, req.chassis_number, req.target_username)
    if not success:
        raise HTTPException(400, msg)
    dealer = get_dealer_snapshot(req.dealer_id)
    if not dealer:
        raise HTTPException(404, "Dealer not found")
    return {"inventory": dealer["inventory"], "sold": dealer["sold_vehicles"]}

@app.post("/book-service")
async def book_service(req: ServiceRequest):
    center = None
    if req.center_id:
        center = next((c for c in SERVICE_CENTERS if c["id"] == req.center_id), None)
    if not center and req.location_lat is not None and req.location_lon is not None:
        center = get_nearest_service_centers(req.location_lat, req.location_lon)[0]
    if not center:
        raise HTTPException(400, "Center not provided and no location to infer nearest")

    ticket_id = f"SRV-{random.randint(10000,99999)}"
    booking = {
        "ticket_id": ticket_id,
        "vehicle_id": req.chassis_number,
        "owner_name": req.owner_name,
        "issue": req.issue,
        "dealer_name": req.dealer_name,
        "service_center": center["name"],
        "center_id": center["id"],
        "distance_km": center.get("distance_km"),
        "estimated_wait_time_minutes": center.get("estimated_wait_time_minutes", random.randint(20, 90)),
        "created_at": datetime.utcnow().isoformat(),
    }

    # Dual notification pathways
    _notify_manager(center, booking)
    _notify_fleet(booking)

    record_service_booking(
        ticket_id,
        req.chassis_number,
        req.owner_name,
        req.issue,
        center["id"],
        center["name"],
    )
    print(f"🔔 NEW SERVICE TICKET: {booking}")
    return booking

# --- SIMULATION & WEBSOCKET (Standard) ---
ATTACK_MODE = False
alert_service = AlertTriggerService()
VEHICLE_HEALTH_HISTORY: Dict[str, List[Dict[str, Any]]] = {}
UEBA_CACHE: Dict[str, Dict[str, Any]] = {}

# --- SAMPLE SERVICE CENTER DATA ---
SERVICE_CENTERS = [
    {"id": "SC_MUMBAI", "name": "Mumbai Central Service", "lat": 19.0760, "lon": 72.8777, "manager": "mumbai.manager@svc.local"},
    {"id": "SC_PUNE", "name": "Pune Express Service", "lat": 18.5204, "lon": 73.8567, "manager": "pune.manager@svc.local"},
    {"id": "SC_NAVI", "name": "Navi Mumbai AutoCare", "lat": 19.0330, "lon": 73.0297, "manager": "navi.manager@svc.local"},
]

@app.post("/toggle-attack/{status}")
async def toggle_attack(status: bool):
    global ATTACK_MODE
    ATTACK_MODE = status
    return {"status": "Attack Mode ON" if status else "Normal Mode"}

def generate_telemetry(chassis_number):
    if ATTACK_MODE:
        return {
            "vehicle_id": chassis_number,
            "temperature": 103.5,
            "vibration": 6.2,
            "rpm": 4500,
            "force_block": True,
            "oil_quality_contaminants_V_oil": 0.18,
            "vibration_rms_A_rms": 6.5,
            "brake_pad_wear_percent": 82,
            "battery_soh_percent": 54,
            "transmission_fluid_temp_C": 121.0,
            "fuel_pressure_kPa": 130.0,
            "vehicle_type": "ambulance",
            "ev_battery_temp_C": 65.0,
            "ev_voltage_stability": 0.2,
            "petrol_knock_index": 0.7,
            "petrol_fuel_trim": 18.0,
            "truck_axle_load_imbalance": 0.3,
            "truck_brake_air_pressure": 75.0,
            "ambulance_high_rpm_flag": True,
            "motorcycle_vibration": 5.5,
            "motorcycle_lean_angle_deg": 48.0,
            "motorcycle_regulator_temp_C": 98.0,
            "motorcycle_methane_ppm": 15.0,
            "petrol_air_fuel_ratio": 20.0,
            "petrol_injector_duty_cycle": 95.0,
            "petrol_cranking_latency_ms": 650,
            "petrol_delta_fuel_pressure_kPa": -40.0,
            "truck_exhaust_temp_C": 780.0,
            "truck_thermal_variance": 0.8,
            "truck_turbo_boost_kPa": 210.0,
            "ambulance_suspension_load": 0.85,
            "ambulance_cabin_co2_ppm": 1800,
            "ambulance_o2_tank_percent": 32,
            "ambulance_fridge_temp_C": 12.5,
            "ambulance_suction_pressure_kPa": 45.0,
            "ambulance_iv_flow_rate_ml_min": 10.0,
            "ev_igbt_temp_C": 115.0,
            "ev_stator_temp_C": 140.0,
            "ev_rotor_alignment_error": 0.35,
            "ev_bearing_vibration": 6.5,
            "ev_cell_delta_V": 0.18,
            "ev_internal_resistance_mOhm": 15.0,
            "ev_contactor_temp_C": 105.0,
        }
    return {
        "vehicle_id": chassis_number,
        "temperature": round(random.uniform(85, 98), 1),
        "vibration": round(random.uniform(0.5, 3.5), 1),
        "rpm": int(random.uniform(1000, 3000)),
        "force_block": False,
        "oil_quality_contaminants_V_oil": round(random.uniform(0.35, 0.95), 2),
        "vibration_rms_A_rms": round(random.uniform(0.6, 3.5), 2),
        "brake_pad_wear_percent": random.randint(10, 75),
        "battery_soh_percent": random.randint(70, 100),
        "transmission_fluid_temp_C": round(random.uniform(75, 110), 1),
        "fuel_pressure_kPa": round(random.uniform(220, 400), 1),
        "vehicle_type": random.choice(["EV", "Petrol", "Truck", "Ambulance", "Motorcycle"]),
        "ev_battery_temp_C": round(random.uniform(30, 55), 1),
        "ev_voltage_stability": round(random.uniform(0.8, 1.0), 2),
        "petrol_knock_index": round(random.uniform(0.05, 0.3), 2),
        "petrol_fuel_trim": round(random.uniform(-5, 10), 1),
        "truck_axle_load_imbalance": round(random.uniform(0, 0.2), 2),
        "truck_brake_air_pressure": round(random.uniform(80, 120), 1),
        "ambulance_high_rpm_flag": False,
        "motorcycle_vibration": round(random.uniform(0.5, 3.0), 2),
        "motorcycle_lean_angle_deg": round(random.uniform(5, 45), 1),
        "motorcycle_regulator_temp_C": round(random.uniform(45, 85), 1),
        "motorcycle_methane_ppm": round(random.uniform(0, 5), 2),
        "petrol_air_fuel_ratio": round(random.uniform(12, 16), 2),
        "petrol_injector_duty_cycle": round(random.uniform(30, 75), 1),
        "petrol_cranking_latency_ms": round(random.uniform(120, 380), 1),
        "petrol_delta_fuel_pressure_kPa": round(random.uniform(-10, 10), 2),
        "truck_exhaust_temp_C": round(random.uniform(350, 650), 1),
        "truck_thermal_variance": round(random.uniform(0.05, 0.3), 2),
        "truck_turbo_boost_kPa": round(random.uniform(120, 190), 1),
        "ambulance_suspension_load": round(random.uniform(0.2, 0.7), 2),
        "ambulance_cabin_co2_ppm": round(random.uniform(600, 1200), 0),
        "ambulance_o2_tank_percent": round(random.uniform(40, 100), 1),
        "ambulance_fridge_temp_C": round(random.uniform(2, 8), 1),
        "ambulance_suction_pressure_kPa": round(random.uniform(60, 90), 1),
        "ambulance_iv_flow_rate_ml_min": round(random.uniform(15, 50), 1),
        "ev_igbt_temp_C": round(random.uniform(60, 95), 1),
        "ev_stator_temp_C": round(random.uniform(70, 110), 1),
        "ev_rotor_alignment_error": round(random.uniform(0.0, 0.15), 2),
        "ev_bearing_vibration": round(random.uniform(0.5, 3.0), 2),
        "ev_cell_delta_V": round(random.uniform(0.01, 0.05), 3),
        "ev_internal_resistance_mOhm": round(random.uniform(2.0, 6.0), 2),
        "ev_contactor_temp_C": round(random.uniform(45, 75), 1),
    }


def _record_vehicle_health(sample: Dict[str, Any]):
    history = VEHICLE_HEALTH_HISTORY.setdefault(sample["vehicle_id"], [])
    history.append({**sample, "timestamp": datetime.utcnow().isoformat()})
    # Keep last 300 entries (~simulated 30-day window for demo)
    if len(history) > 300:
        del history[0: len(history) - 300]


def _telemetry_behavior_flags(sample: Dict[str, Any]) -> Dict[str, Any]:
    flags = {}
    impossible = []
    if sample.get("temperature", 0) < -50 or sample.get("temperature", 0) > 200:
        impossible.append("temperature")
    if sample.get("vehicle_type") == "EV" and sample.get("petrol_knock_index"):
        flags["vehicle_type_mismatch"] = True
    if sample.get("vehicle_type") == "Petrol" and sample.get("ev_battery_temp_C"):
        flags["vehicle_type_mismatch"] = True
    if impossible:
        flags["impossible_values"] = True
    if sample.get("vibration", 0) > 15 or sample.get("truck_axle_load_imbalance", 0) > 0.9:
        flags["inconsistent_sensors"] = True
    return flags

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    await websocket.accept()
    vid = websocket.query_params.get("vehicle_id", "UNKNOWN")
    role = websocket.query_params.get("role", "user")
    try:
        while True:
            raw = generate_telemetry(vid)
            _record_vehicle_health(raw)

            # Predictive risk + alerting
            model_output = predict_breakdown_risk(raw)
            alert = alert_service.evaluate(model_output)

            res = await agent_workflow.ainvoke(raw | {"risk_score_numeric": model_output["risk_score"], "root_cause_sensor": model_output["root_cause_sensor"], "predicted_failure_type": model_output["predicted_failure_type"]})

            # UEBA advanced
            telemetry_flags = _telemetry_behavior_flags(raw)
            web_alerts = {"score": 0, "findings": []}
            ueba_output = ueba_analyze(
                user_behavior={"failed_logins": 0, "ip_change": False, "odd_questions": False},
                manager_behavior={"unauthorized_access": False, "high_freq_ops": False},
                telemetry=telemetry_flags,
                web_alerts=web_alerts,
            )
            UEBA_CACHE[vid] = ueba_output
            ueba_view = apply_access_control(role if role else "user", ueba_output)

            payload = {
                **raw,
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "risk_score": res.get("risk_score"),
                "risk_score_numeric": model_output["risk_score"],
                "predicted_failure_type": model_output["predicted_failure_type"],
                "root_cause_sensor": model_output["root_cause_sensor"],
                "repair_recommendation": res.get("repair_recommendation"),
                "security_decision": res.get("security_decision"),
                "logs": res.get("diagnosis_log", []),
                "alert": alert,
                "ueba": ueba_view,
            }
            await websocket.send_text(json.dumps(payload))
            await asyncio.sleep(3)
    except WebSocketDisconnect:
        pass


# --- HEALTH DASHBOARD ENDPOINTS ---
@app.get("/vehicle/{chassis_number}/health")
async def vehicle_health(chassis_number: str):
    history = VEHICLE_HEALTH_HISTORY.get(chassis_number, [])
    if not history:
        raise HTTPException(404, "No telemetry yet for vehicle")
    current = history[-1]
    return {"current": current}


@app.get("/vehicle/{chassis_number}/health/trend")
async def vehicle_health_trend(chassis_number: str):
    history = VEHICLE_HEALTH_HISTORY.get(chassis_number, [])
    if not history:
        raise HTTPException(404, "No telemetry yet for vehicle")
    # Return last 30 (represents 30-day in demo)
    trend = history[-30:]
    return {"points": trend}


# --- ALERTS & CHATBOT ---
@app.get("/alerts/active")
async def active_alerts():
    return {"alerts": alert_service.active_alerts}


@app.post("/chatbot/query")
async def chatbot_query(payload: ChatbotQuery):
    chassis_number = payload.chassis_number
    question = payload.question
    history = VEHICLE_HEALTH_HISTORY.get(chassis_number, [])
    latest = history[-1] if history else None
    alert = alert_service.get_alert_for_vehicle(chassis_number)

    model_output = predict_breakdown_risk(latest) if latest else {"risk_score": 0, "predicted_failure_type": "Unknown", "root_cause_sensor": "unknown"}
    rca_output = None
    if latest:
        res = await agent_workflow.ainvoke(latest | {
            "risk_score_numeric": model_output.get("risk_score", 0),
            "root_cause_sensor": model_output.get("root_cause_sensor"),
            "predicted_failure_type": model_output.get("predicted_failure_type"),
        })
        rca_output = res.get("repair_recommendation")
    # Web alerts (if available via request middleware) default to benign
    web_alerts = {"score": 0, "findings": []}
    ueba_output = ueba_analyze(
        user_behavior={"failed_logins": 0, "ip_change": False, "odd_questions": "why" in question.lower()},
        manager_behavior={"unauthorized_access": False, "high_freq_ops": False},
        telemetry=_telemetry_behavior_flags(latest or {}),
        web_alerts=web_alerts,
    )
    UEBA_CACHE[chassis_number] = ueba_output

    ai_resp = generate_ai_response(question, latest, alert, rca_output)

    # Backward-compatible fields
    if alert:
        explanation = (
            f"The alert is for {alert['predicted_failure_type']} because "
            f"{alert['root_cause_sensor']} is currently {alert['current_sensor_value']} (risk {alert['risk_score']:.2f})."
        )
    else:
        explanation = "No active alerts. All systems within nominal ranges."

    question_lower = question.lower()
    subsystem_hint = ""
    if "brake" in question_lower:
        if latest:
            subsystem_hint = f"Brake pad wear is {latest.get('brake_pad_wear_percent')}%."
    elif "battery" in question_lower:
        if latest:
            subsystem_hint = f"Battery SOH is {latest.get('battery_soh_percent')}%."
    elif "transmission" in question_lower:
        if latest:
            subsystem_hint = f"Transmission fluid temp is {latest.get('transmission_fluid_temp_C')}C."
    elif "fuel" in question_lower:
        if latest:
            subsystem_hint = f"Fuel pressure is {latest.get('fuel_pressure_kPa')} kPa."

    return {
        "vehicle_id": chassis_number,
        "explanation": explanation,
        "subsystem": subsystem_hint or "Ask about brakes, battery, transmission, or fuel for details.",
        # New AI fields
        "answer": ai_resp["answer"],
        "risk_level": ai_resp["risk_level"],
        "most_likely_cause": ai_resp["most_likely_cause"],
        "recommended_action": ai_resp["recommended_action"],
        "urgency": ai_resp["urgency"],
        "predicted_failure_type": ai_resp.get("predicted_failure_type"),
        "root_cause_sensor": ai_resp.get("root_cause_sensor"),
        "ueba": apply_access_control("user", ueba_output),
    }


# --- SERVICE CENTER DISCOVERY ---
def _haversine(lat1, lon1, lat2, lon2):
    from math import radians, sin, cos, sqrt, atan2
    R = 6371  # km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c


def get_nearest_service_centers(location_lat: float, location_lon: float):
    centers = []
    for c in SERVICE_CENTERS:
        dist = _haversine(location_lat, location_lon, c["lat"], c["lon"])
        centers.append({
            **c,
            "distance_km": round(dist, 2),
            "estimated_wait_time_minutes": random.randint(20, 90),
        })
    return sorted(centers, key=lambda x: x["distance_km"])


@app.get("/service-centers/nearest")
async def nearest_centers(req: ServiceCenterRequest):
    return {"centers": get_nearest_service_centers(req.location_lat, req.location_lon)}


# --- ROBUST BOOKING & NOTIFICATIONS ---
def _notify_manager(center, booking):
    print(f"[Manager Notify] -> {center['manager']} | Booking: {booking}")


def _notify_fleet(booking):
    print(f"[Fleet Notify] -> fleet@autodoc.local | Booking: {booking}")


@app.get("/manager/bookings")
async def manager_bookings(center_id: Optional[str] = None):
    return {"bookings": list_service_bookings(center_id)}


@app.get("/security/logs")
async def security_logs():
    return {"logs": SECURITY_LOGS[-200:]}


@app.get("/security/ueba/{chassis_number}")
async def security_ueba(chassis_number: str):
    return {"vehicle_id": chassis_number, "ueba": UEBA_CACHE.get(chassis_number, {"ueba_status": "NORMAL", "ueba_score": 0, "ueba_findings": ["No data"]})}