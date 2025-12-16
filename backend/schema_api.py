from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any

app = FastAPI(
    title="AutoDoc Schema API",
    description="Auto-generates documentation from schema.sql",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Schema extracted from your schema.sql
SCHEMA = {
    "database": "autodoc",
    "description": "Vehicle Telematics & Maintenance Platform with RCM (Reliability Centered Maintenance)",
    "tables": {
        "users": {
            "description": "Core user accounts (OWNER, FLEET_MGR, MECHANIC, ADMIN)",
            "primary_key": "user_id",
            "columns": [
                {"name": "user_id", "type": "UUID", "nullable": False, "default": "gen_random_uuid()"},
                {"name": "username", "type": "VARCHAR(50)", "nullable": False, "constraints": "UNIQUE"},
                {"name": "full_name", "type": "VARCHAR(100)", "nullable": False},
                {"name": "role", "type": "VARCHAR(20)", "nullable": False, "check": "OWNER|FLEET_MGR|MECHANIC|ADMIN"},
                {"name": "email", "type": "VARCHAR(100)", "nullable": False, "constraints": "UNIQUE"},
                {"name": "password_hash", "type": "TEXT", "nullable": False},
                {"name": "phone", "type": "VARCHAR(20)", "nullable": True},
                {"name": "created_at", "type": "TIMESTAMP", "nullable": False, "default": "NOW()"}
            ]
        },
        "dealers": {
            "description": "Dealer metadata mapped to privileged users",
            "primary_key": "dealer_id",
            "columns": [
                {"name": "dealer_id", "type": "UUID", "nullable": False, "default": "gen_random_uuid()"},
                {"name": "user_id", "type": "UUID", "nullable": True, "foreign_key": "users(user_id)", "on_delete": "CASCADE", "constraints": "UNIQUE"},
                {"name": "location", "type": "VARCHAR(100)", "nullable": True},
                {"name": "contact", "type": "VARCHAR(30)", "nullable": True}
            ]
        },
        "vehicles": {
            "description": "Digital Twin root - vehicle catalog (License Plate as PK)",
            "primary_key": "vehicle_id",
            "columns": [
                {"name": "vehicle_id", "type": "VARCHAR(50)", "nullable": False, "note": "License Plate e.g., MH12-AB-1234"},
                {"name": "dealer_id", "type": "UUID", "nullable": True, "foreign_key": "dealers(dealer_id)", "on_delete": "SET NULL"},
                {"name": "owner_id", "type": "UUID", "nullable": True, "foreign_key": "users(user_id)", "on_delete": "SET NULL"},
                {"name": "category", "type": "VARCHAR(20)", "nullable": False, "check": "2W_CNG|4W_CNG|HCV_CNG|AMBULANCE|EV_PV|EV_FLEET"},
                {"name": "make", "type": "VARCHAR(50)", "nullable": True},
                {"name": "model", "type": "VARCHAR(50)", "nullable": True},
                {"name": "manufacturing_year", "type": "INT", "nullable": True},
                {"name": "is_active", "type": "BOOLEAN", "nullable": False, "default": "TRUE"},
                {"name": "sale_date", "type": "TIMESTAMP", "nullable": True},
                {"name": "last_service_date", "type": "TIMESTAMP", "nullable": True}
            ]
        },
        "sensor_thresholds": {
            "description": "RCM threshold configuration rules",
            "primary_key": "rule_id",
            "columns": [
                {"name": "rule_id", "type": "SERIAL", "nullable": False},
                {"name": "vehicle_category", "type": "VARCHAR(20)", "nullable": True},
                {"name": "parameter_name", "type": "VARCHAR(50)", "nullable": True},
                {"name": "min_val", "type": "DECIMAL(10,2)", "nullable": True},
                {"name": "max_val", "type": "DECIMAL(10,2)", "nullable": True},
                {"name": "unit", "type": "VARCHAR(10)", "nullable": True},
                {"name": "severity_level", "type": "VARCHAR(10)", "nullable": True, "check": "LOW|MEDIUM|CRITICAL"}
            ]
        },
        "telemetry_stream": {
            "description": "High-velocity telemetry data with JSONB flexible payload",
            "primary_key": "event_id",
            "columns": [
                {"name": "event_id", "type": "BIGSERIAL", "nullable": False},
                {"name": "vehicle_id", "type": "VARCHAR(50)", "nullable": False, "foreign_key": "vehicles(vehicle_id)", "on_delete": "CASCADE"},
                {"name": "timestamp", "type": "TIMESTAMP", "nullable": False, "default": "NOW()"},
                {"name": "latitude", "type": "DECIMAL(9,6)", "nullable": True},
                {"name": "longitude", "type": "DECIMAL(9,6)", "nullable": True},
                {"name": "speed_kmh", "type": "DECIMAL(5,2)", "nullable": True},
                {"name": "sensor_data", "type": "JSONB", "nullable": True, "note": "Flexible payload for sensor readings"}
            ],
            "indexes": [
                "idx_telemetry_vehicle_time (vehicle_id, timestamp DESC)",
                "idx_telemetry_json_battery ((sensor_data->>'cell_voltage_delta'))",
                "idx_telemetry_json_egt ((sensor_data->>'exhaust_gas_temp'))"
            ]
        },
        "maintenance_incidents": {
            "description": "AI-generated maintenance alerts from RCM analysis",
            "primary_key": "incident_id",
            "columns": [
                {"name": "incident_id", "type": "UUID", "nullable": False, "default": "gen_random_uuid()"},
                {"name": "vehicle_id", "type": "VARCHAR(50)", "nullable": False, "foreign_key": "vehicles(vehicle_id)", "on_delete": "CASCADE"},
                {"name": "detected_at", "type": "TIMESTAMP", "nullable": False, "default": "NOW()"},
                {"name": "failure_type", "type": "VARCHAR(100)", "nullable": True},
                {"name": "root_cause", "type": "TEXT", "nullable": True},
                {"name": "recommended_action", "type": "TEXT", "nullable": True},
                {"name": "status", "type": "VARCHAR(20)", "nullable": False, "check": "OPEN|ACKNOWLEDGED|WORK_IN_PROGRESS|RESOLVED"},
                {"name": "service_appointment_id", "type": "UUID", "nullable": True}
            ]
        },
        "service_bookings": {
            "description": "Dealer service workflow management",
            "primary_key": "booking_id",
            "columns": [
                {"name": "booking_id", "type": "UUID", "nullable": False, "default": "gen_random_uuid()"},
                {"name": "ticket_id", "type": "VARCHAR(30)", "nullable": False, "constraints": "UNIQUE"},
                {"name": "vehicle_id", "type": "VARCHAR(50)", "nullable": False, "foreign_key": "vehicles(vehicle_id)", "on_delete": "CASCADE"},
                {"name": "owner_id", "type": "UUID", "nullable": True, "foreign_key": "users(user_id)", "on_delete": "SET NULL"},
                {"name": "dealer_id", "type": "UUID", "nullable": True, "foreign_key": "dealers(dealer_id)", "on_delete": "SET NULL"},
                {"name": "service_center_id", "type": "VARCHAR(50)", "nullable": False},
                {"name": "service_center_name", "type": "VARCHAR(100)", "nullable": False},
                {"name": "issue", "type": "TEXT", "nullable": True},
                {"name": "created_at", "type": "TIMESTAMP", "nullable": False, "default": "NOW()"},
                {"name": "status", "type": "VARCHAR(20)", "nullable": True, "default": "OPEN"}
            ]
        }
    },
    "relationships": [
        {"from": "dealers.user_id", "to": "users.user_id", "type": "ONE_TO_ONE", "cascade": "CASCADE"},
        {"from": "vehicles.dealer_id", "to": "dealers.dealer_id", "type": "MANY_TO_ONE", "cascade": "SET NULL"},
        {"from": "vehicles.owner_id", "to": "users.user_id", "type": "MANY_TO_ONE", "cascade": "SET NULL"},
        {"from": "telemetry_stream.vehicle_id", "to": "vehicles.vehicle_id", "type": "MANY_TO_ONE", "cascade": "CASCADE"},
        {"from": "maintenance_incidents.vehicle_id", "to": "vehicles.vehicle_id", "type": "MANY_TO_ONE", "cascade": "CASCADE"},
        {"from": "service_bookings.vehicle_id", "to": "vehicles.vehicle_id", "type": "MANY_TO_ONE", "cascade": "CASCADE"},
        {"from": "service_bookings.owner_id", "to": "users.user_id", "type": "MANY_TO_ONE", "cascade": "SET NULL"},
        {"from": "service_bookings.dealer_id", "to": "dealers.dealer_id", "type": "MANY_TO_ONE", "cascade": "SET NULL"}
    ],
    "extensions": ["pgcrypto"],
    "statistics": {
        "total_tables": 7,
        "total_relationships": 8,
        "total_columns": 56,
        "total_indexes": 3
    }
}

@app.get("/")
async def root():
    return {
        "message": "AutoDoc Schema API - Vehicle Telematics Platform",
        "status": "running",
        "version": "1.0.0",
        "database": SCHEMA["database"],
        "docs_url": "/docs"
    }

@app.get("/api/schema/summary")
async def get_schema_summary():
    """Returns overall schema summary"""
    return {
        "database": SCHEMA["database"],
        "description": SCHEMA["description"],
        "statistics": SCHEMA["statistics"],
        "extensions": SCHEMA["extensions"]
    }

@app.get("/api/schema/tables")
async def get_all_tables():
    """Returns all tables with metadata"""
    tables_list = []
    for table_name, table_info in SCHEMA["tables"].items():
        tables_list.append({
            "table_name": table_name,
            "description": table_info["description"],
            "primary_key": table_info["primary_key"],
            "column_count": len(table_info["columns"])
        })
    return {
        "tables": tables_list,
        "total_count": len(tables_list)
    }

@app.get("/api/schema/table/{table_name}")
async def get_table_details(table_name: str):
    """Returns detailed structure of a specific table"""
    if table_name not in SCHEMA["tables"]:
        return {
            "error": f"Table '{table_name}' not found",
            "available_tables": list(SCHEMA["tables"].keys())
        }
    
    table = SCHEMA["tables"][table_name]
    return {
        "table_name": table_name,
        "description": table["description"],
        "primary_key": table["primary_key"],
        "columns": table["columns"],
        "column_count": len(table["columns"]),
        "indexes": table.get("indexes", [])
    }

@app.get("/api/schema/relationships")
async def get_relationships():
    """Returns all foreign key relationships"""
    return {
        "relationships": SCHEMA["relationships"],
        "total_count": len(SCHEMA["relationships"])
    }

@app.get("/api/schema/export")
async def export_schema():
    """Exports complete schema as JSON"""
    return SCHEMA

@app.get("/api/schema/er-diagram")
async def get_er_diagram():
    """Returns ER diagram in mermaid format"""
    mermaid = "erDiagram\n"
    
    for table_name, table_info in SCHEMA["tables"].items():
        mermaid += f'    {table_name} {{\n'
        for col in table_info["columns"]:
            col_type = col["type"].replace("(", "_").replace(")", "")
            mermaid += f'        {col_type} {col["name"]}\n'
        mermaid += '    }\n'
    
    for rel in SCHEMA["relationships"]:
        from_table = rel["from"].split(".")[0]
        to_table = rel["to"].split(".")[0]
        mermaid += f'    {from_table} ||--o{{ {to_table} : ""\n'
    
    return {
        "format": "mermaid",
        "diagram": mermaid,
        "render_url": "https://mermaid.live"
    }