# AutoDoc Feature & Security Overview

This document summarizes current functionality, new telemetry/prediction, booking, security, and chatbot capabilities. It is **additive** and does not change existing behavior.

## Core Functional Areas
- **Auth**: `/login` supports dealer (`DLR_TATA`, `DLR_MAHINDRA`) and users (`rahul`, `priya`, `amit`).
- **Inventory & Assignment**: Dealers add stock (`/dealer/add-stock`) and assign vehicles (`/dealer/assign`) to users.
- **Telemetry & WS**: WebSocket `/ws/{client_id}?vehicle_id=...&role=...` streams telemetry, risk, RCA, alerts, UEBA view, and logs.
- **Booking**: `/book-service` creates service tickets with center selection or nearest inference; manager booking view via `/manager/bookings`.
- **Service Centers**: `/service-centers/nearest` returns sorted centers with distance and estimated wait.

## Predictive Telemetry (Multi-Vehicle)
Optional sensors; absence does not break clients.
- Engine/core: temperature, vibration, rpm, oil_quality_contaminants_V_oil, vibration_rms_A_rms, brake_pad_wear_percent, battery_soh_percent, transmission_fluid_temp_C, fuel_pressure_kPa.
- EV: ev_battery_temp_C, ev_voltage_stability, ev_igbt_temp_C, ev_stator_temp_C, ev_rotor_alignment_error, ev_bearing_vibration, ev_cell_delta_V, ev_internal_resistance_mOhm, ev_contactor_temp_C.
- Petrol: petrol_knock_index, petrol_fuel_trim, petrol_air_fuel_ratio, petrol_injector_duty_cycle, petrol_cranking_latency_ms, petrol_delta_fuel_pressure_kPa.
- Truck: truck_axle_load_imbalance, truck_brake_air_pressure, truck_exhaust_temp_C, truck_thermal_variance, truck_turbo_boost_kPa.
- Ambulance: ambulance_high_rpm_flag, ambulance_suspension_load, ambulance_cabin_co2_ppm, ambulance_o2_tank_percent, ambulance_fridge_temp_C, ambulance_suction_pressure_kPa, ambulance_iv_flow_rate_ml_min.
- Motorcycle: motorcycle_vibration, motorcycle_lean_angle_deg, motorcycle_regulator_temp_C, motorcycle_methane_ppm.
- Vehicle type: `vehicle_type` in {EV, Petrol, Truck, Ambulance, Motorcycle} with type-aware risk multipliers.

## Prediction & RCA
- Weighted risk computation in `predictive.py` and `agent_graph.py` with vehicle-type adjustments.
- RCA mappings cover all sensors; outputs `repair_recommendation` and `predicted_failure_type`.

## Alerts & UEBA
- **Alerts**: `AlertTriggerService` emits structured alerts when risk > threshold (default 0.85).
- **UEBA**: `ueba_engine.analyze` combines user/manager behavior flags, telemetry anomalies, and WAF-lite signals into `ueba_score`, `ueba_status`, `ueba_findings`.
- **Access Control**: `apply_access_control(role, ueba_output)` shows full detail to managers, simplified findings to users.
- **Security Logs**: WAF-lite middleware logs suspicious requests; `GET /security/logs` returns recent entries. UEBA cache per vehicle: `GET /security/ueba/{vehicle_id}`.

## Web Security (WAF-lite)
- `request_security.py` middleware scans for SQLi/XSS/traversal, payload anomalies, rapid rate; attaches `request_security_score` to request state; logs findings (no blocking).

## Chatbot (AI-Style Assistant)
- Endpoint: `POST /chatbot/query` (backward compatible). Returns legacy fields plus AI fields: `answer`, `risk_level`, `most_likely_cause`, `recommended_action`, `urgency`, and `ueb`a view.
- Logic: `intelligent_chatbot.py` uses telemetry, risk, RCA, alerts, vehicle type, and UEBA context to produce senior-engineer style responses.

## Frontend Additions
- User dashboard: Live telemetry, RCA, booking button, extended telemetry tiles, Data Integrity Status card (UEBA), AI chatbot panel with quick questions and active alerts.
- Dealer/Manager dashboard: Inventory/sales remain; added ManagerBookings table and UEBA Security Center table for recent security logs.

## Data Persistence
- Dealer/user auth, inventory, sales history, and service bookings now live in PostgreSQL via the schema in `schema.sql` (SQLAlchemy models in `backend/database.py`). 
- `VEHICLE_HEALTH_HISTORY`, `SECURITY_LOGS`, `UEBA_CACHE` remain runtime-memory constructs for real-time telemetry and security context.

## Compatibility Notes
- No existing endpoints or fields were removed/renamed.
- All new fields are optional; missing sensors default safely.
- WebSocket payloads only append fields, keeping legacy clients working.

