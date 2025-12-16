import psycopg2
import json
import random
import time
from datetime import datetime, timedelta

# ==========================================
# 1. CONFIGURATION (CRITICAL)
# ==========================================
DB_CONFIG = {
    "dbname": "fleet_management_v3", 
    "user": "postgres",
    "password": "Prerita#12",  # <--- STOP! CHANGE THIS TO YOUR REAL PASSWORD
    "host": "localhost",
    "port": "5432"
}

# ==========================================
# 2. SQL COMMANDS (Creates Tables First)
# ==========================================
SQL_SETUP = [
    """CREATE EXTENSION IF NOT EXISTS "pgcrypto";""",
    
    """DO $$ BEGIN 
        CREATE TYPE vehicle_type_enum AS ENUM ('2W', '3W', '4W', 'HV'); 
    EXCEPTION 
        WHEN duplicate_object THEN null; 
    END $$;""",
    
    """DO $$ BEGIN 
        CREATE TYPE fuel_type_enum AS ENUM ('PETROL', 'DIESEL', 'EV', 'CNG'); 
    EXCEPTION 
        WHEN duplicate_object THEN null; 
    END $$;""",

    """CREATE TABLE IF NOT EXISTS users (
        user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        username VARCHAR(50) UNIQUE NOT NULL,
        full_name VARCHAR(100) NOT NULL,
        role VARCHAR(20) CHECK (role IN ('OWNER', 'FLEET_MGR', 'MECHANIC', 'ADMIN', 'EMPLOYEE')),
        email VARCHAR(100) UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT NOW()
    );""",

    """CREATE TABLE IF NOT EXISTS dealers (
        dealer_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
        location VARCHAR(100),
        contact VARCHAR(30)
    );""",

    """CREATE TABLE IF NOT EXISTS vehicles (
        chassis_number VARCHAR(50) PRIMARY KEY,
        vehicle_number VARCHAR(20),
        dealer_id UUID REFERENCES dealers(dealer_id) ON DELETE SET NULL,
        owner_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
        authorized_operators UUID[], 
        make VARCHAR(50),
        model VARCHAR(50),
        type vehicle_type_enum NOT NULL,
        fuel_type fuel_type_enum NOT NULL,
        manufacturing_year INT,
        is_active BOOLEAN DEFAULT TRUE,
        sale_date TIMESTAMP
    );""",

    """CREATE TABLE IF NOT EXISTS telemetry_stream (
        event_id BIGSERIAL PRIMARY KEY,
        chassis_number VARCHAR(50) REFERENCES vehicles(chassis_number) ON DELETE CASCADE,
        timestamp TIMESTAMP DEFAULT NOW(),
        latitude DECIMAL(9, 6),
        longitude DECIMAL(9, 6),
        speed_kmh DECIMAL(5, 2),
        sensor_data JSONB 
    );""",

    # Seed Data (Dealers)
    """INSERT INTO users (username, full_name, role, email, password_hash) VALUES
    ('HERO_DLR', 'Hero MotoCorp Delhi', 'ADMIN', 'hero@auto.local', 'hashed_pass_placeholder')
    ON CONFLICT (username) DO NOTHING;""",

    """INSERT INTO dealers (user_id, location, contact)
    SELECT user_id, 'New Delhi', '1800-HERO' FROM users WHERE username = 'HERO_DLR'
    ON CONFLICT DO NOTHING;"""
]

# Vehicles to register
VEHICLES = [
    {"chassis": "VIN-10001-XA", "make": "Hero MotoCorp", "model": "Splendor Plus", "type": "2W", "fuel": "PETROL"},
    {"chassis": "VIN-10002-XB", "make": "Mahindra & Mahindra", "model": "Thar", "type": "4W", "fuel": "DIESEL"},
    {"chassis": "VIN-10003-XC", "make": "Hero MotoCorp", "model": "Vida V1", "type": "2W", "fuel": "EV"},
    {"chassis": "VIN-10004-XD", "make": "Mahindra & Mahindra", "model": "Blazo", "type": "HV", "fuel": "DIESEL"}
]

def run_setup():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        cur = conn.cursor()
        
        print("1. Setting up Database Schema...")
        for cmd in SQL_SETUP:
            cur.execute(cmd)
            
        print("2. Registering Vehicles...")
        cur.execute("SELECT dealer_id FROM dealers LIMIT 1;")
        res = cur.fetchone()
        if not res:
            print("ERROR: No dealers found. Check INSERT statements.")
            return
        dealer_id = res[0]
        
        for v in VEHICLES:
            # Check if exists
            cur.execute("SELECT 1 FROM vehicles WHERE chassis_number = %s", (v["chassis"],))
            if not cur.fetchone():
                query = """
                    INSERT INTO vehicles (chassis_number, dealer_id, make, model, type, fuel_type, is_active, manufacturing_year)
                    VALUES (%s, %s, %s, %s, %s, %s, TRUE, 2024);
                """
                cur.execute(query, (v["chassis"], dealer_id, v["make"], v["model"], v["type"], v["fuel"]))
        
        print("3. Generating Telemetry...")
        for _ in range(50):
            v = random.choice(VEHICLES)
            data = json.dumps({"rpm": random.randint(1000,5000)})
            cur.execute("INSERT INTO telemetry_stream (chassis_number, speed_kmh, sensor_data) VALUES (%s, %s, %s)", 
                       (v["chassis"], random.randint(10,100), data))
            
        print("\n✅ SUCCESS! Database is ready.")
        cur.close()
        conn.close()
        
    except Exception as e:
        print("\n❌ ERROR:", e)
        print("-> Did you update the password in DB_CONFIG?")

if __name__ == "__main__":
    run_setup()