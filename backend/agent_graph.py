from typing import TypedDict, Literal, Optional
from langgraph.graph import StateGraph, START, END

# --- 0. SIMULATED KNOWLEDGE BASE (RAG) ---
# Maps specific failure signatures to engineering fixes
KNOWLEDGE_BASE = {
    "overheat_instability": {
        "issue": "Thermostat Gasket Failure & Loose Engine Mounts",
        "action": "Replace Head Gasket (Part #HG-99) and tighten mounts to 50Nm.",
        "priority": "CRITICAL"
    },
    "overheat_only": {
        "issue": "Coolant Leak or Radiator Blockage",
        "action": "Top up coolant and inspect radiator fins.",
        "priority": "HIGH"
    },
    "oil_quality_low": {
        "issue": "Oil Contamination / Viscosity Loss",
        "action": "Schedule oil flush and filter replacement; sample oil for lab test.",
        "priority": "HIGH"
    },
    "brake_pad_wear": {
        "issue": "Brake Pad Wear Near Limit",
        "action": "Replace front pads and inspect rotors; recalibrate brake bias.",
        "priority": "HIGH"
    },
    "battery_health_low": {
        "issue": "Battery State-of-Health Degraded",
        "action": "Run load test; clean terminals; plan pre-emptive replacement.",
        "priority": "MEDIUM"
    },
    "transmission_overheat": {
        "issue": "Transmission Fluid Overheating",
        "action": "Inspect cooler; flush transmission fluid; check pump operation.",
        "priority": "CRITICAL"
    },
    "fuel_pressure_low": {
        "issue": "Low Fuel Rail Pressure",
        "action": "Inspect fuel pump and filter; check for injector leakage.",
        "priority": "MEDIUM"
    },
    "ev_thermal_risk": {
        "issue": "EV Battery Thermal Stress",
        "action": "Reduce load, check coolant loop, schedule pack thermal inspection.",
        "priority": "CRITICAL"
    },
    "ev_voltage_instability": {
        "issue": "EV Voltage Instability",
        "action": "Inspect inverter DC link and HV cabling; run BMS diagnostics.",
        "priority": "HIGH"
    },
    "petrol_knock": {
        "issue": "Petrol Engine Knock Risk",
        "action": "Check fuel quality, timing advance, and knock sensor harness.",
        "priority": "HIGH"
    },
    "petrol_fuel_trim": {
        "issue": "Fuel Trim Deviation",
        "action": "Inspect O2 sensors, vacuum leaks, and injector balance.",
        "priority": "MEDIUM"
    },
    "truck_load_imbalance": {
        "issue": "Axle Load Imbalance",
        "action": "Redistribute cargo; inspect suspension and load cells.",
        "priority": "MEDIUM"
    },
    "truck_brake_air": {
        "issue": "Brake Air Pressure Low",
        "action": "Inspect compressor, lines, and check for leaks; top up air.",
        "priority": "CRITICAL"
    },
    "ambulance_high_duty": {
        "issue": "High Duty Cycle Risk",
        "action": "Increase cooldown intervals; prioritize urgent maintenance slot.",
        "priority": "CRITICAL"
    }
}

# --- 1. STATE ---
class AgentState(TypedDict, total=False):
    chassis_number: str
    temperature: float
    vibration: float
    force_block: bool
    oil_quality_contaminants_V_oil: float
    vibration_rms_A_rms: float
    brake_pad_wear_percent: int
    battery_soh_percent: int
    transmission_fluid_temp_C: float
    fuel_pressure_kPa: float
    vehicle_type: str
    ev_battery_temp_C: float
    ev_voltage_stability: float
    petrol_knock_index: float
    petrol_fuel_trim: float
    truck_axle_load_imbalance: float
    truck_brake_air_pressure: float
    ambulance_high_rpm_flag: bool
    motorcycle_vibration: float
    motorcycle_lean_angle_deg: float
    motorcycle_regulator_temp_C: float
    motorcycle_methane_ppm: float
    petrol_air_fuel_ratio: float
    petrol_injector_duty_cycle: float
    petrol_cranking_latency_ms: float
    petrol_delta_fuel_pressure_kPa: float
    truck_exhaust_temp_C: float
    truck_thermal_variance: float
    truck_turbo_boost_kPa: float
    ambulance_suspension_load: float
    ambulance_cabin_co2_ppm: float
    ambulance_o2_tank_percent: float
    ambulance_fridge_temp_C: float
    ambulance_suction_pressure_kPa: float
    ambulance_iv_flow_rate_ml_min: float
    ev_igbt_temp_C: float
    ev_stator_temp_C: float
    ev_rotor_alignment_error: float
    ev_bearing_vibration: float
    ev_cell_delta_V: float
    ev_internal_resistance_mOhm: float
    ev_contactor_temp_C: float

    risk_score: str
    risk_score_numeric: float
    predicted_failure_type: Optional[str]
    root_cause_sensor: Optional[str]
    diagnosis_log: list
    security_decision: str
    # NEW: The Engineering Fix
    repair_recommendation: Optional[dict]

# --- 2. NODES ---
def _weighted_risk_score(state: AgentState):
    """Combine traditional signals with new high-fidelity telematics."""
    weights = {
        "temperature": 0.15,
        "vibration": 0.1,
        "oil_quality_contaminants_V_oil": 0.2,
        "vibration_rms_A_rms": 0.15,
        "brake_pad_wear_percent": 0.1,
        "battery_soh_percent": 0.1,
        "transmission_fluid_temp_C": 0.15,
        "fuel_pressure_kPa": 0.05,
        "ev_battery_temp_C": 0.12,
        "ev_voltage_stability": 0.1,
        "petrol_knock_index": 0.12,
        "petrol_fuel_trim": 0.08,
        "truck_axle_load_imbalance": 0.1,
        "truck_brake_air_pressure": 0.12,
        "ambulance_high_rpm_flag": 0.08,
        "motorcycle_vibration": 0.08,
        "motorcycle_lean_angle_deg": 0.05,
        "motorcycle_regulator_temp_C": 0.06,
        "motorcycle_methane_ppm": 0.04,
        "petrol_air_fuel_ratio": 0.06,
        "petrol_injector_duty_cycle": 0.06,
        "petrol_cranking_latency_ms": 0.04,
        "petrol_delta_fuel_pressure_kPa": 0.05,
        "truck_exhaust_temp_C": 0.08,
        "truck_thermal_variance": 0.05,
        "truck_turbo_boost_kPa": 0.05,
        "ambulance_suspension_load": 0.05,
        "ambulance_cabin_co2_ppm": 0.05,
        "ambulance_o2_tank_percent": 0.08,
        "ambulance_fridge_temp_C": 0.04,
        "ambulance_suction_pressure_kPa": 0.05,
        "ambulance_iv_flow_rate_ml_min": 0.04,
        "ev_igbt_temp_C": 0.06,
        "ev_stator_temp_C": 0.05,
        "ev_rotor_alignment_error": 0.05,
        "ev_bearing_vibration": 0.05,
        "ev_cell_delta_V": 0.04,
        "ev_internal_resistance_mOhm": 0.04,
        "ev_contactor_temp_C": 0.04,
    }

    # Normalize features to 0..1 where higher means riskier
    norm = {
        "temperature": max(0, (state.get("temperature", 0) - 85) / 25),
        "vibration": min(1, state.get("vibration", 0) / 6),
        "oil_quality_contaminants_V_oil": max(0, 1 - state.get("oil_quality_contaminants_V_oil", 1)),  # lower is worse
        "vibration_rms_A_rms": min(1, state.get("vibration_rms_A_rms", 0) / 8),
        "brake_pad_wear_percent": min(1, state.get("brake_pad_wear_percent", 0) / 100),
        "battery_soh_percent": max(0, 1 - state.get("battery_soh_percent", 100) / 100),
        "transmission_fluid_temp_C": max(0, (state.get("transmission_fluid_temp_C", 0) - 80) / 60),
        "fuel_pressure_kPa": max(0, (350 - state.get("fuel_pressure_kPa", 350)) / 250),
        "ev_battery_temp_C": max(0, (state.get("ev_battery_temp_C", 0) - 40) / 35),
        "ev_voltage_stability": max(0, 1 - state.get("ev_voltage_stability", 1)),
        "petrol_knock_index": min(1, state.get("petrol_knock_index", 0) / 1.0),
        "petrol_fuel_trim": min(1, abs(state.get("petrol_fuel_trim", 0)) / 25),
        "truck_axle_load_imbalance": min(1, state.get("truck_axle_load_imbalance", 0)),
        "truck_brake_air_pressure": max(0, (90 - state.get("truck_brake_air_pressure", 90)) / 40),
        "ambulance_high_rpm_flag": 1.0 if state.get("ambulance_high_rpm_flag") else 0.0,
        "motorcycle_vibration": min(1, state.get("motorcycle_vibration", 0) / 6),
        "motorcycle_lean_angle_deg": min(1, state.get("motorcycle_lean_angle_deg", 0) / 60),
        "motorcycle_regulator_temp_C": max(0, (state.get("motorcycle_regulator_temp_C", 0) - 70) / 50),
        "motorcycle_methane_ppm": min(1, state.get("motorcycle_methane_ppm", 0) / 50),
        "petrol_air_fuel_ratio": min(1, abs(14.7 - state.get("petrol_air_fuel_ratio", 14.7)) / 10),
        "petrol_injector_duty_cycle": min(1, state.get("petrol_injector_duty_cycle", 0) / 100),
        "petrol_cranking_latency_ms": min(1, state.get("petrol_cranking_latency_ms", 0) / 800),
        "petrol_delta_fuel_pressure_kPa": min(1, abs(state.get("petrol_delta_fuel_pressure_kPa", 0)) / 80),
        "truck_exhaust_temp_C": max(0, (state.get("truck_exhaust_temp_C", 0) - 450) / 400),
        "truck_thermal_variance": min(1, state.get("truck_thermal_variance", 0) / 1.0),
        "truck_turbo_boost_kPa": max(0, (state.get("truck_turbo_boost_kPa", 0) - 180) / 80),
        "ambulance_suspension_load": min(1, state.get("ambulance_suspension_load", 0) / 1.0),
        "ambulance_cabin_co2_ppm": max(0, (state.get("ambulance_cabin_co2_ppm", 400) - 800) / 2000),
        "ambulance_o2_tank_percent": max(0, (50 - state.get("ambulance_o2_tank_percent", 100)) / 50),
        "ambulance_fridge_temp_C": max(0, (state.get("ambulance_fridge_temp_C", 0) - 8) / 12),
        "ambulance_suction_pressure_kPa": max(0, (70 - state.get("ambulance_suction_pressure_kPa", 70)) / 40),
        "ambulance_iv_flow_rate_ml_min": max(0, (10 - state.get("ambulance_iv_flow_rate_ml_min", 40)) / 40),
        "ev_igbt_temp_C": max(0, (state.get("ev_igbt_temp_C", 0) - 80) / 70),
        "ev_stator_temp_C": max(0, (state.get("ev_stator_temp_C", 0) - 90) / 70),
        "ev_rotor_alignment_error": min(1, state.get("ev_rotor_alignment_error", 0) / 0.5),
        "ev_bearing_vibration": min(1, state.get("ev_bearing_vibration", 0) / 6),
        "ev_cell_delta_V": min(1, state.get("ev_cell_delta_V", 0) / 0.2),
        "ev_internal_resistance_mOhm": max(0, (state.get("ev_internal_resistance_mOhm", 2) - 6) / 20),
        "ev_contactor_temp_C": max(0, (state.get("ev_contactor_temp_C", 0) - 70) / 50),
    }

    risk_score = sum(norm[k] * w for k, w in weights.items())
    vehicle_type = state.get("vehicle_type")
    if vehicle_type == "EV":
        risk_score *= 1.05
    elif vehicle_type == "Petrol":
        risk_score *= 1.02
    elif vehicle_type == "Truck":
        risk_score *= 1.07
    elif vehicle_type == "Ambulance":
        risk_score *= 1.1
    elif vehicle_type == "Motorcycle":
        risk_score *= 1.03

    # Pick dominant contributor
    top_sensor = max(norm.items(), key=lambda kv: kv[1])[0]
    return min(1.0, risk_score), top_sensor, norm[top_sensor]


def _failure_label(sensor: str):
    mapping = {
        "oil_quality_contaminants_V_oil": "Engine Seizure Risk due to oil contamination",
        "vibration_rms_A_rms": "Drivetrain imbalance / bearing fatigue",
        "brake_pad_wear_percent": "Brake Fade Risk from worn pads",
        "battery_soh_percent": "Electrical system instability (battery SOH low)",
        "transmission_fluid_temp_C": "Transmission Overheating",
        "fuel_pressure_kPa": "Fuel delivery instability (low rail pressure)",
        "temperature": "Engine Overheating",
        "vibration": "Engine mount / accessory imbalance",
        "ev_battery_temp_C": "EV Battery Thermal Risk",
        "ev_voltage_stability": "EV Voltage Instability",
        "petrol_knock_index": "Engine Knock Detected",
        "petrol_fuel_trim": "Fuel Trim Out of Range",
        "truck_axle_load_imbalance": "Axle Load Imbalance",
        "truck_brake_air_pressure": "Brake Air Pressure Low",
        "ambulance_high_rpm_flag": "High Duty RPM Pattern",
        "motorcycle_vibration": "Motorcycle Vibration High",
        "motorcycle_lean_angle_deg": "Aggressive Lean Angle",
        "motorcycle_regulator_temp_C": "Regulator Overheating",
        "motorcycle_methane_ppm": "Methane Detected Near Bike",
        "petrol_air_fuel_ratio": "Air-Fuel Ratio Out of Range",
        "petrol_injector_duty_cycle": "Injector Duty Cycle High",
        "petrol_cranking_latency_ms": "Slow Cranking Detected",
        "petrol_delta_fuel_pressure_kPa": "Fuel Pressure Delta Abnormal",
        "truck_exhaust_temp_C": "High Exhaust Temp",
        "truck_thermal_variance": "Thermal Variance High",
        "truck_turbo_boost_kPa": "Turbo Boost Over Spec",
        "ambulance_suspension_load": "Suspension Load High",
        "ambulance_cabin_co2_ppm": "Cabin CO2 Elevated",
        "ambulance_o2_tank_percent": "O2 Tank Low",
        "ambulance_fridge_temp_C": "Fridge Temperature High",
        "ambulance_suction_pressure_kPa": "Suction Pressure Low",
        "ambulance_iv_flow_rate_ml_min": "IV Flow Rate Low",
        "ev_igbt_temp_C": "IGBT Temperature High",
        "ev_stator_temp_C": "Stator Temperature High",
        "ev_rotor_alignment_error": "Rotor Alignment Error",
        "ev_bearing_vibration": "Bearing Vibration High",
        "ev_cell_delta_V": "Cell Voltage Delta High",
        "ev_internal_resistance_mOhm": "Internal Resistance Rising",
        "ev_contactor_temp_C": "Contactor Temperature High",
    }
    return mapping.get(sensor, "General Instability Detected")


def diagnosis_node(state: AgentState):
    temp = state["temperature"]
    vibration = state["vibration"]
    logs = state.get("diagnosis_log", [])

    risk_numeric, dominant_sensor, dominant_value = _weighted_risk_score(state)
    if risk_numeric > 0.75:
        risk = "HIGH_RISK"
    elif risk_numeric > 0.45:
        risk = "MODERATE_RISK"
    else:
        risk = "NORMAL"

    reason = (
        f"Risk {risk_numeric:.2f} driven by {dominant_sensor} (norm {dominant_value:.2f}); "
        f"T={temp}C, Vib={vibration}g"
    )

    predicted_failure = _failure_label(dominant_sensor)

    return {
        "risk_score": risk,
        "risk_score_numeric": round(risk_numeric, 3),
        "predicted_failure_type": predicted_failure,
        "root_cause_sensor": dominant_sensor,
        "diagnosis_log": logs + [reason],
        "repair_recommendation": None,  # Reset previous recommendations
    }

def ueba_node(state: AgentState):
    logs = state["diagnosis_log"]
    force_block = state.get("force_block", False)

    if force_block:
        decision = "BLOCKED"
        log_entry = "SECURITY ALERT: Anomalous command signature detected."
    else:
        decision = "APPROVED"
        log_entry = "UEBA Scan: Behavior within policy limits."

    return {
        "security_decision": decision,
        "diagnosis_log": logs + [log_entry],
    }

# NEW: RCA Node 🔧
def rca_node(state: AgentState):
    temp = state["temperature"]
    vibration = state["vibration"]
    logs = state["diagnosis_log"]
    root_sensor = state.get("root_cause_sensor")

    # Simple logic to choose the right knowledge base entry
    if temp > 95 and vibration > 4:
        insight = KNOWLEDGE_BASE["overheat_instability"]
        log_entry = "RCA Agent: Correlated Heat+Vib to specific gasket failure."
    elif temp > 95:
        insight = KNOWLEDGE_BASE["overheat_only"]
        log_entry = "RCA Agent: Identified potential coolant system leak."
    elif root_sensor == "oil_quality_contaminants_V_oil":
        insight = KNOWLEDGE_BASE["oil_quality_low"]
        log_entry = "RCA Agent: Low oil quality linked to lubrication risk."
    elif root_sensor == "brake_pad_wear_percent":
        insight = KNOWLEDGE_BASE["brake_pad_wear"]
        log_entry = "RCA Agent: Brake wear approaching limits."
    elif root_sensor == "battery_soh_percent":
        insight = KNOWLEDGE_BASE["battery_health_low"]
        log_entry = "RCA Agent: Battery SOH degradation noted."
    elif root_sensor == "transmission_fluid_temp_C":
        insight = KNOWLEDGE_BASE["transmission_overheat"]
        log_entry = "RCA Agent: Transmission fluid overheating pattern."
    elif root_sensor == "fuel_pressure_kPa":
        insight = KNOWLEDGE_BASE["fuel_pressure_low"]
        log_entry = "RCA Agent: Fuel pressure below nominal."
    elif root_sensor == "ev_battery_temp_C":
        insight = KNOWLEDGE_BASE["ev_thermal_risk"]
        log_entry = "RCA Agent: EV battery thermal elevation."
    elif root_sensor == "ev_voltage_stability":
        insight = KNOWLEDGE_BASE["ev_voltage_instability"]
        log_entry = "RCA Agent: EV voltage instability detected."
    elif root_sensor == "petrol_knock_index":
        insight = KNOWLEDGE_BASE["petrol_knock"]
        log_entry = "RCA Agent: Petrol knock pattern observed."
    elif root_sensor == "petrol_fuel_trim":
        insight = KNOWLEDGE_BASE["petrol_fuel_trim"]
        log_entry = "RCA Agent: Fuel trim deviation detected."
    elif root_sensor == "truck_axle_load_imbalance":
        insight = KNOWLEDGE_BASE["truck_load_imbalance"]
        log_entry = "RCA Agent: Axle load imbalance risk."
    elif root_sensor == "truck_brake_air_pressure":
        insight = KNOWLEDGE_BASE["truck_brake_air"]
        log_entry = "RCA Agent: Truck brake air pressure low."
    elif root_sensor == "ambulance_high_rpm_flag":
        insight = KNOWLEDGE_BASE["ambulance_high_duty"]
        log_entry = "RCA Agent: Ambulance high-RPM duty pattern."
    elif root_sensor == "motorcycle_vibration":
        insight = {"issue": "Motorcycle vibration spike", "action": "Inspect chain tension, engine mounts, and tires.", "priority": "MEDIUM"}
        log_entry = "RCA Agent: Motorcycle vibration elevated."
    elif root_sensor == "motorcycle_lean_angle_deg":
        insight = {"issue": "Aggressive lean angle detected", "action": "Advise rider caution; inspect tire wear and traction control.", "priority": "LOW"}
        log_entry = "RCA Agent: High lean angle pattern."
    elif root_sensor == "motorcycle_regulator_temp_C":
        insight = {"issue": "Regulator/rectifier overheating", "action": "Check cooling airflow and connector corrosion.", "priority": "HIGH"}
        log_entry = "RCA Agent: Regulator temp high."
    elif root_sensor == "motorcycle_methane_ppm":
        insight = {"issue": "Methane presence near motorcycle", "action": "Inspect fuel system for leaks; ensure ventilation.", "priority": "HIGH"}
        log_entry = "RCA Agent: Methane detection elevated."
    elif root_sensor == "petrol_air_fuel_ratio":
        insight = {"issue": "Air-Fuel ratio out of range", "action": "Check O2 sensors, MAF, vacuum leaks; adjust fueling.", "priority": "MEDIUM"}
        log_entry = "RCA Agent: AFR deviation."
    elif root_sensor == "petrol_injector_duty_cycle":
        insight = {"issue": "Injector duty high", "action": "Check fuel pump, filter, and injector balance.", "priority": "MEDIUM"}
        log_entry = "RCA Agent: Injector duty elevated."
    elif root_sensor == "petrol_cranking_latency_ms":
        insight = {"issue": "Cranking latency high", "action": "Test battery, starter relay, and fuel prime pressure.", "priority": "MEDIUM"}
        log_entry = "RCA Agent: Slow crank detected."
    elif root_sensor == "petrol_delta_fuel_pressure_kPa":
        insight = {"issue": "Fuel pressure delta abnormal", "action": "Inspect regulator and rail sensor; verify pump output.", "priority": "MEDIUM"}
        log_entry = "RCA Agent: Fuel pressure delta issue."
    elif root_sensor == "truck_exhaust_temp_C":
        insight = {"issue": "Exhaust temperature high", "action": "Check DPF regen status and turbo health.", "priority": "HIGH"}
        log_entry = "RCA Agent: Truck exhaust temp high."
    elif root_sensor == "truck_thermal_variance":
        insight = {"issue": "Thermal variance high", "action": "Inspect cooling distribution and clogged fins.", "priority": "MEDIUM"}
        log_entry = "RCA Agent: Thermal variance elevated."
    elif root_sensor == "truck_turbo_boost_kPa":
        insight = {"issue": "Turbo boost over spec", "action": "Check wastegate, boost leaks, and turbo control valve.", "priority": "HIGH"}
        log_entry = "RCA Agent: Turbo boost high."
    elif root_sensor == "ambulance_suspension_load":
        insight = {"issue": "Suspension load high", "action": "Redistribute load; inspect shocks and air springs.", "priority": "HIGH"}
        log_entry = "RCA Agent: Suspension load elevated."
    elif root_sensor == "ambulance_cabin_co2_ppm":
        insight = {"issue": "Cabin CO2 elevated", "action": "Improve ventilation; check HVAC filters.", "priority": "HIGH"}
        log_entry = "RCA Agent: Cabin CO2 high."
    elif root_sensor == "ambulance_o2_tank_percent":
        insight = {"issue": "O2 tank low", "action": "Refill/replace O2 tank; verify regulators.", "priority": "CRITICAL"}
        log_entry = "RCA Agent: O2 level low."
    elif root_sensor == "ambulance_fridge_temp_C":
        insight = {"issue": "Fridge temperature high", "action": "Check compressor and seals; move perishables.", "priority": "HIGH"}
        log_entry = "RCA Agent: Fridge temp high."
    elif root_sensor == "ambulance_suction_pressure_kPa":
        insight = {"issue": "Suction pressure low", "action": "Inspect tubing, pump, and filter; verify power.", "priority": "CRITICAL"}
        log_entry = "RCA Agent: Suction pressure low."
    elif root_sensor == "ambulance_iv_flow_rate_ml_min":
        insight = {"issue": "IV flow rate low", "action": "Check IV line for kinks; confirm pump settings.", "priority": "CRITICAL"}
        log_entry = "RCA Agent: IV flow low."
    elif root_sensor == "ev_igbt_temp_C":
        insight = {"issue": "IGBT temperature high", "action": "Check inverter cooling loop; derate power.", "priority": "CRITICAL"}
        log_entry = "RCA Agent: IGBT temp high."
    elif root_sensor == "ev_stator_temp_C":
        insight = {"issue": "Stator temperature high", "action": "Inspect coolant flow and motor load.", "priority": "HIGH"}
        log_entry = "RCA Agent: Stator temp high."
    elif root_sensor == "ev_rotor_alignment_error":
        insight = {"issue": "Rotor alignment error", "action": "Run alignment calibration; inspect encoder.", "priority": "HIGH"}
        log_entry = "RCA Agent: Rotor alignment error."
    elif root_sensor == "ev_bearing_vibration":
        insight = {"issue": "Bearing vibration high", "action": "Inspect bearings and lubrication.", "priority": "HIGH"}
        log_entry = "RCA Agent: Bearing vibration high."
    elif root_sensor == "ev_cell_delta_V":
        insight = {"issue": "Cell voltage delta high", "action": "Balance cells; run BMS diagnostics.", "priority": "HIGH"}
        log_entry = "RCA Agent: Cell delta high."
    elif root_sensor == "ev_internal_resistance_mOhm":
        insight = {"issue": "Internal resistance rising", "action": "Assess pack aging; plan replacement.", "priority": "MEDIUM"}
        log_entry = "RCA Agent: Internal resistance elevated."
    elif root_sensor == "ev_contactor_temp_C":
        insight = {"issue": "Contactor temperature high", "action": "Inspect contactor duty cycle and cooling.", "priority": "HIGH"}
        log_entry = "RCA Agent: Contactor temp high."
    else:
        insight = None
        log_entry = "RCA Agent: No failure pattern match."

    return {
        "repair_recommendation": insight,
        "diagnosis_log": logs + [log_entry],
    }

# --- 3. GRAPH FLOW ---
def check_risk_level(state: AgentState) -> Literal["ueba_check", "end_process"]:
    if state["risk_score"] == "HIGH_RISK" or state["risk_score"] == "MODERATE_RISK":
        return "ueba_check"
    return "end_process"

workflow = StateGraph(AgentState)
workflow.add_node("diagnosis", diagnosis_node)
workflow.add_node("ueba_check", ueba_node)
workflow.add_node("rca_insight", rca_node) # Add RCA Node

workflow.add_edge(START, "diagnosis")

workflow.add_conditional_edges(
    "diagnosis",
    check_risk_level,
    {
        "ueba_check": "ueba_check", 
        "end_process": END
    }
)

# After Security Check, ALWAYS run RCA to give insights (even if blocked)
workflow.add_edge("ueba_check", "rca_insight")
workflow.add_edge("rca_insight", END)

agent_workflow = workflow.compile()