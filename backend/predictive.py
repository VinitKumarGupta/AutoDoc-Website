from typing import Dict, Any, Tuple

def _get_val(value: Any) -> float:
    """
    Helper: Extracts the mean value if the sensor data is a V3 'Redundant' dictionary.
    Otherwise returns the float value directly.
    """
    if isinstance(value, dict) and "sensor_1" in value:
        return (value["sensor_1"] + value.get("sensor_2", value["sensor_1"])) / 2
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0

def _normalize(telemetry: Dict[str, Any]) -> Dict[str, float]:
    # We use _get_val to safely handle both simple floats AND V3 redundant packets
    return {
        "temperature": max(0, (_get_val(telemetry.get("temperature", 0)) - 85) / 25),
        "vibration": min(1, _get_val(telemetry.get("vibration", 0)) / 6),
        "oil_quality_contaminants_V_oil": max(0, 1 - _get_val(telemetry.get("oil_quality_contaminants_V_oil", 1))),
        "vibration_rms_A_rms": min(1, _get_val(telemetry.get("vibration_rms_A_rms", 0)) / 8),
        "brake_pad_wear_percent": min(1, _get_val(telemetry.get("brake_pad_wear_percent", 0)) / 100),
        "battery_soh_percent": max(0, 1 - _get_val(telemetry.get("battery_soh_percent", 100)) / 100),
        "transmission_fluid_temp_C": max(0, (_get_val(telemetry.get("transmission_fluid_temp_C", 0)) - 80) / 60),
        "fuel_pressure_kPa": max(0, (350 - _get_val(telemetry.get("fuel_pressure_kPa", 350))) / 250),
        "ev_battery_temp_C": max(0, (_get_val(telemetry.get("ev_battery_temp_C", 0)) - 40) / 35),
        "ev_voltage_stability": max(0, 1 - _get_val(telemetry.get("ev_voltage_stability", 1))),
        "petrol_knock_index": min(1, _get_val(telemetry.get("petrol_knock_index", 0)) / 1.0),
        "petrol_fuel_trim": min(1, abs(_get_val(telemetry.get("petrol_fuel_trim", 0))) / 25),
        "truck_axle_load_imbalance": min(1, _get_val(telemetry.get("truck_axle_load_imbalance", 0))),
        "truck_brake_air_pressure": max(0, (90 - _get_val(telemetry.get("truck_brake_air_pressure", 90))) / 40),
        "ambulance_high_rpm_flag": 1.0 if telemetry.get("ambulance_high_rpm_flag") else 0.0,
        "motorcycle_vibration": min(1, _get_val(telemetry.get("motorcycle_vibration", 0)) / 6),
        "motorcycle_lean_angle_deg": min(1, _get_val(telemetry.get("motorcycle_lean_angle_deg", 0)) / 60),
        "motorcycle_regulator_temp_C": max(0, (_get_val(telemetry.get("motorcycle_regulator_temp_C", 0)) - 70) / 50),
        "motorcycle_methane_ppm": min(1, _get_val(telemetry.get("motorcycle_methane_ppm", 0)) / 50),
        "petrol_air_fuel_ratio": min(1, abs(14.7 - _get_val(telemetry.get("petrol_air_fuel_ratio", 14.7))) / 10),
        "petrol_injector_duty_cycle": min(1, _get_val(telemetry.get("petrol_injector_duty_cycle", 0)) / 100),
        "petrol_cranking_latency_ms": min(1, _get_val(telemetry.get("petrol_cranking_latency_ms", 0)) / 800),
        "petrol_delta_fuel_pressure_kPa": min(1, abs(_get_val(telemetry.get("petrol_delta_fuel_pressure_kPa", 0))) / 80),
        "truck_exhaust_temp_C": max(0, (_get_val(telemetry.get("truck_exhaust_temp_C", 0)) - 450) / 400),
        "truck_thermal_variance": min(1, _get_val(telemetry.get("truck_thermal_variance", 0)) / 1.0),
        "truck_turbo_boost_kPa": max(0, (_get_val(telemetry.get("truck_turbo_boost_kPa", 0)) - 180) / 80),
        "ambulance_suspension_load": min(1, _get_val(telemetry.get("ambulance_suspension_load", 0)) / 1.0),
        "ambulance_cabin_co2_ppm": max(0, (_get_val(telemetry.get("ambulance_cabin_co2_ppm", 400)) - 800) / 2000),
        "ambulance_o2_tank_percent": max(0, (50 - _get_val(telemetry.get("ambulance_o2_tank_percent", 100))) / 50),
        "ambulance_fridge_temp_C": max(0, (_get_val(telemetry.get("ambulance_fridge_temp_C", 0)) - 8) / 12),
        "ambulance_suction_pressure_kPa": max(0, (70 - _get_val(telemetry.get("ambulance_suction_pressure_kPa", 70))) / 40),
        "ambulance_iv_flow_rate_ml_min": max(0, (10 - _get_val(telemetry.get("ambulance_iv_flow_rate_ml_min", 40))) / 40),
        "ev_igbt_temp_C": max(0, (_get_val(telemetry.get("ev_igbt_temp_C", 0)) - 80) / 70),
        "ev_stator_temp_C": max(0, (_get_val(telemetry.get("ev_stator_temp_C", 0)) - 90) / 70),
        "ev_rotor_alignment_error": min(1, _get_val(telemetry.get("ev_rotor_alignment_error", 0)) / 0.5),
        "ev_bearing_vibration": min(1, _get_val(telemetry.get("ev_bearing_vibration", 0)) / 6),
        "ev_cell_delta_V": min(1, _get_val(telemetry.get("ev_cell_delta_V", 0)) / 0.2),
        "ev_internal_resistance_mOhm": max(0, (_get_val(telemetry.get("ev_internal_resistance_mOhm", 2)) - 6) / 20),
        "ev_contactor_temp_C": max(0, (_get_val(telemetry.get("ev_contactor_temp_C", 0)) - 70) / 50),
    }

def _weights():
    return {
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

def _failure_label(sensor: str):
    mapping = {
        "oil_quality_contaminants_V_oil": "Engine Seizure Risk due to low oil quality",
        "vibration_rms_A_rms": "Drivetrain imbalance (RMS vibration high)",
        "brake_pad_wear_percent": "Brake Fade Risk (pads near limit)",
        "battery_soh_percent": "Electrical instability (battery SOH low)",
        "transmission_fluid_temp_C": "Transmission Overheating",
        "fuel_pressure_kPa": "Fuel delivery instability (rail pressure low)",
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


def predict_breakdown_risk(telemetry: Dict[str, Any]) -> Dict[str, Any]:
    """Return a weighted risk score and dominant failure hypothesis."""
    norm = _normalize(telemetry)
    weight_map = _weights()

    risk_score = sum(norm[k] * weight_map[k] for k in weight_map)
    risk_score = min(1.0, risk_score)
    vehicle_type = telemetry.get("vehicle_type")
    
    # Adjust risk multiplier based on vehicle type
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

    # Find dominant sensor
    dominant_sensor = max(norm.items(), key=lambda kv: kv[1])[0] if norm else "unknown"
    
    # Get the raw value for the dominant sensor (handling the dict/float issue)
    raw_val_struct = telemetry.get(dominant_sensor)
    current_value = _get_val(raw_val_struct)

    predicted_failure = _failure_label(dominant_sensor)

    return {
        "vehicle_id": telemetry.get("vehicle_id", telemetry.get("chassis_number", "UNKNOWN")),
        "risk_score": round(risk_score, 3),
        "predicted_failure_type": predicted_failure,
        "root_cause_sensor": dominant_sensor,
        "current_sensor_value": current_value,
    }