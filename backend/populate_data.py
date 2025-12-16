import psycopg2
import json
import random
from datetime import datetime, timedelta

# ==========================================
# CONFIGURATION
# ==========================================
DB_CONFIG = {
    "dbname": "fleet_management_v3", 
    "user": "postgres",
    "password": "Prerita#12", # Your DB Password
    "host": "localhost",
    "port": "5432"
}

# ==========================================
# SQL SCHEMA & SEED DATA
# ==========================================
SQL_SETUP = [
    """CREATE EXTENSION IF NOT EXISTS "pgcrypto";""",
    
    # ENUMS
    """DO $$ BEGIN CREATE TYPE vehicle_type_enum AS ENUM ('2W', '3W', '4W', 'HV'); EXCEPTION WHEN duplicate_object THEN null; END $$;""",
    """DO $$ BEGIN CREATE TYPE fuel_type_enum AS ENUM ('PETROL', 'DIESEL', 'EV', 'CNG'); EXCEPTION WHEN duplicate_object THEN null; END $$;""",

    # 1. USERS & DEALERS
    """CREATE TABLE IF NOT EXISTS users (
        user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        username VARCHAR(50) UNIQUE NOT NULL,
        full_name VARCHAR(100) NOT NULL,
        role VARCHAR(20),
        email VARCHAR(100),
        password_hash TEXT,
        created_at TIMESTAMP DEFAULT NOW()
    );""",

    """CREATE TABLE IF NOT EXISTS dealers (
        dealer_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
        location VARCHAR(100),
        contact VARCHAR(30)
    );""",

    # 2. VEHICLES
    """CREATE TABLE IF NOT EXISTS vehicles (
        chassis_number VARCHAR(50) PRIMARY KEY,
        dealer_id UUID REFERENCES dealers(dealer_id) ON DELETE SET NULL,
        owner_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
        make VARCHAR(50),
        model VARCHAR(50),
        type vehicle_type_enum,
        fuel_type fuel_type_enum,
        manufacturing_year INT,
        is_active BOOLEAN DEFAULT TRUE,
        sale_date TIMESTAMP
    );""",

    # 3. TELEMETRY
    """CREATE TABLE IF NOT EXISTS telemetry_stream (
        event_id BIGSERIAL PRIMARY KEY,
        chassis_number VARCHAR(50) REFERENCES vehicles(chassis_number),
        timestamp TIMESTAMP DEFAULT NOW(),
        speed_kmh DECIMAL(5, 2),
        sensor_data JSONB 
    );""",

    # 4. MAINTENANCE HISTORY (New for Agents)
    """CREATE TABLE IF NOT EXISTS maintenance_history (
        history_id SERIAL PRIMARY KEY,
        chassis_number VARCHAR(50) REFERENCES vehicles(chassis_number),
        service_date DATE,
        service_type VARCHAR(100),
        description TEXT,
        cost DECIMAL(10, 2)
    );""",

    # 5. CAPA / RCA RECORDS (New for Agents)
    """CREATE TABLE IF NOT EXISTS capa_records (
        capa_id SERIAL PRIMARY KEY,
        component VARCHAR(100),
        defect_type VARCHAR(100),
        action_required TEXT,
        batch_id VARCHAR(50)
    );""",

    # 6. APPOINTMENTS (New for Scheduler)
    """CREATE TABLE IF NOT EXISTS appointments (
        appt_id SERIAL PRIMARY KEY,
        slot_time VARCHAR(20),
        is_booked BOOLEAN DEFAULT FALSE,
        booked_chassis VARCHAR(50)
    );"""
]

# REALISTIC DATA
DEALER_USER = ("HERO_DLR", "Hero MotoCorp Delhi", "ADMIN", "hero@auto.local")
VEHICLES = [
    {"chassis": "VIN-10001-XA", "make": "Hero", "model": "Splendor Plus", "type": "2W", "fuel": "PETROL"},
    {"chassis": "VIN-10002-XB", "make": "Mahindra", "model": "Thar", "type": "4W", "fuel": "DIESEL"},
    {"chassis": "VIN-10003-XC", "make": "Hero", "model": "Vida V1", "type": "2W", "fuel": "EV"},
    {"chassis": "VIN-10004-XD", "make": "Mahindra", "model": "Blazo", "type": "HV", "fuel": "DIESEL"}
]
CAPA_DATA = [
    ("Coolant Sensor", "Seal Failure", "Replace with Part #992-B (Upgraded Gasket)", "Batch-992"),
    ("Battery Pack", "Thermal Runaway Risk", "Check BMS firmware version 2.1", "Batch-EV-101"),
    ("Brake Pads", "Premature Wear", "Inspect caliper alignment", "Batch-BRK-55")
]

def run_setup():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        cur = conn.cursor()
        print("🚀 Setting up PostgreSQL for Fleet V3...")

        # 1. Schema
        for sql in SQL_SETUP:
            cur.execute(sql)

        # 2. Seed Dealer
        cur.execute("INSERT INTO users (username, full_name, role, email, password_hash) VALUES (%s, %s, %s, %s, 'hash') ON CONFLICT DO NOTHING", DEALER_USER)
        cur.execute("SELECT user_id FROM users WHERE username = %s", (DEALER_USER[0],))
        dealer_uid = cur.fetchone()[0]
        cur.execute("INSERT INTO dealers (user_id, location, contact) VALUES (%s, 'Delhi', '1800-HERO') ON CONFLICT DO NOTHING", (dealer_uid,))
        cur.execute("SELECT dealer_id FROM dealers WHERE user_id = %s", (dealer_uid,))
        dealer_id = cur.fetchone()[0]

        # 3. Seed Vehicles
        for v in VEHICLES:
            cur.execute("SELECT 1 FROM vehicles WHERE chassis_number = %s", (v["chassis"],))
            if not cur.fetchone():
                cur.execute("""
                    INSERT INTO vehicles (chassis_number, dealer_id, make, model, type, fuel_type, manufacturing_year)
                    VALUES (%s, %s, %s, %s, %s, %s, 2024)
                """, (v["chassis"], dealer_id, v["make"], v["model"], v["type"], v["fuel"]))

        # 4. Seed History & CAPA
        cur.execute("TRUNCATE maintenance_history, capa_records, appointments RESTART IDENTITY;")
        
        # History for Splendor (VIN-10001-XA)
        cur.execute("INSERT INTO maintenance_history (chassis_number, service_date, service_type, description, cost) VALUES (%s, %s, %s, %s, %s)", 
                   ("VIN-10001-XA", "2024-01-15", "Oil Change", "Standard Service", 850))
        
        # CAPA
        for c in CAPA_DATA:
            cur.execute("INSERT INTO capa_records (component, defect_type, action_required, batch_id) VALUES (%s, %s, %s, %s)", c)

        # Appointments
        slots = ["09:00", "10:00", "11:00", "14:00", "15:00"]
        for s in slots:
            cur.execute("INSERT INTO appointments (slot_time, is_booked) VALUES (%s, FALSE)", (s,))

        print("✅ Database Populated Successfully!")
        cur.close()
        conn.close()

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    run_setup()