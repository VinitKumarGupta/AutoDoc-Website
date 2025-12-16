import psycopg2
import json
import random
from datetime import datetime, timedelta

# Import the hashing function so we store REAL hashes, not junk strings
try:
    from database import hash_password
except ImportError:
    # Fallback if running directly without path setup
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    def hash_password(plain): return pwd_context.hash(plain)

# ==========================================
# CONFIGURATION
# ==========================================
DB_CONFIG = {
    "dbname": "fleet_management_v3", 
    "user": "postgres",
    "password": "Prerita#12", 
    "host": "localhost",
    "port": "5432"
}

# ==========================================
# SQL SCHEMA
# ==========================================
SQL_SETUP = [
    """CREATE EXTENSION IF NOT EXISTS "pgcrypto";""",
    
    # DROP TABLES (Clean Slate)
    """DROP TABLE IF EXISTS telemetry_stream CASCADE;""",
    """DROP TABLE IF EXISTS maintenance_history CASCADE;""",
    """DROP TABLE IF EXISTS capa_records CASCADE;""",
    """DROP TABLE IF EXISTS appointments CASCADE;""",
    """DROP TABLE IF EXISTS vehicles CASCADE;""",
    """DROP TABLE IF EXISTS dealers CASCADE;""",
    """DROP TABLE IF EXISTS users CASCADE;""",
    
    # ENUMS
    """DO $$ BEGIN CREATE TYPE vehicle_type_enum AS ENUM ('2W', '3W', '4W', 'HV'); EXCEPTION WHEN duplicate_object THEN null; END $$;""",
    """DO $$ BEGIN CREATE TYPE fuel_type_enum AS ENUM ('PETROL', 'DIESEL', 'EV', 'CNG'); EXCEPTION WHEN duplicate_object THEN null; END $$;""",

    # TABLES
    """CREATE TABLE users (
        user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        username VARCHAR(50) UNIQUE NOT NULL,
        full_name VARCHAR(100) NOT NULL,
        role VARCHAR(20),
        email VARCHAR(100) UNIQUE,
        password_hash TEXT,
        phone VARCHAR(20),
        created_at TIMESTAMP DEFAULT NOW()
    );""",

    """CREATE TABLE dealers (
        dealer_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
        location VARCHAR(100),
        contact VARCHAR(30)
    );""",

    """CREATE TABLE vehicles (
        chassis_number VARCHAR(50) PRIMARY KEY,
        dealer_id UUID REFERENCES dealers(dealer_id) ON DELETE SET NULL,
        owner_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
        category VARCHAR(20),
        make VARCHAR(50),
        model VARCHAR(50),
        manufacturing_year INT,
        is_active BOOLEAN DEFAULT TRUE,
        sale_date TIMESTAMP,
        last_service_date TIMESTAMP,
        fuel_type VARCHAR(20)
    );""",

    """CREATE TABLE telemetry_stream (
        event_id BIGSERIAL PRIMARY KEY,
        chassis_number VARCHAR(50) REFERENCES vehicles(chassis_number) ON DELETE CASCADE,
        timestamp TIMESTAMP DEFAULT NOW(),
        speed_kmh DECIMAL(5, 2),
        sensor_data JSONB 
    );""",

    """CREATE TABLE maintenance_history (
        history_id SERIAL PRIMARY KEY,
        chassis_number VARCHAR(50) REFERENCES vehicles(chassis_number) ON DELETE CASCADE,
        service_date DATE,
        service_type VARCHAR(100),
        description TEXT,
        cost DECIMAL(10, 2)
    );""",

    """CREATE TABLE capa_records (
        capa_id SERIAL PRIMARY KEY,
        component VARCHAR(100),
        defect_type VARCHAR(100),
        action_required TEXT,
        batch_id VARCHAR(50)
    );""",

    """CREATE TABLE appointments (
        appt_id SERIAL PRIMARY KEY,
        slot_time VARCHAR(20),
        is_booked BOOLEAN DEFAULT FALSE,
        booked_chassis VARCHAR(50)
    );"""
]

# ==========================================
# SEED DATA
# ==========================================

# 1. DEALER: Username=HERO_DLR, Password=admin
DEALER_PASS_HASH = hash_password("admin") 
DEALER_USER = ("HERO_DLR", "Hero MotoCorp Delhi", "ADMIN", "hero@auto.local", DEALER_PASS_HASH, "1800-HERO")

VEHICLES = [
    {"chassis": "VIN-10001-XA", "make": "Hero", "model": "Splendor Plus", "cat": "2W", "fuel": "PETROL"},
    {"chassis": "VIN-10002-XB", "make": "Mahindra", "model": "Thar", "cat": "4W", "fuel": "DIESEL"},
    {"chassis": "VIN-10003-XC", "make": "Hero", "model": "Vida V1", "cat": "2W", "fuel": "EV"},
    {"chassis": "VIN-10004-XD", "make": "Mahindra", "model": "Blazo", "cat": "HV", "fuel": "DIESEL"}
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

        # 1. Run Schema
        for sql in SQL_SETUP:
            cur.execute(sql)

        # 2. Seed Dealer (Fixed Insert)
        cur.execute("""
            INSERT INTO users (username, full_name, role, email, password_hash, phone) 
            VALUES (%s, %s, %s, %s, %s, %s) 
            ON CONFLICT (username) DO NOTHING
        """, DEALER_USER)
        
        # Get Dealer ID
        cur.execute("SELECT user_id FROM users WHERE username = %s", (DEALER_USER[0],))
        dealer_uid = cur.fetchone()[0]
        cur.execute("INSERT INTO dealers (user_id, location, contact) VALUES (%s, 'Delhi', '1800-HERO') ON CONFLICT DO NOTHING", (dealer_uid,))
        cur.execute("SELECT dealer_id FROM dealers WHERE user_id = %s", (dealer_uid,))
        dealer_id = cur.fetchone()[0]

        # 3. Seed Vehicles
        for v in VEHICLES:
            cur.execute("""
                INSERT INTO vehicles (chassis_number, dealer_id, make, model, category, fuel_type, manufacturing_year, sale_date)
                VALUES (%s, %s, %s, %s, %s, %s, 2024, NOW())
            """, (v["chassis"], dealer_id, v["make"], v["model"], v["cat"], v["fuel"]))

        # 4. Seed History & CAPA & Appointments
        cur.execute("TRUNCATE maintenance_history, capa_records, appointments RESTART IDENTITY;")
        cur.execute("INSERT INTO maintenance_history (chassis_number, service_date, service_type, description, cost) VALUES (%s, %s, %s, %s, %s)", 
                   ("VIN-10001-XA", "2024-01-15", "Oil Change", "Standard Service", 850))
        
        for c in CAPA_DATA:
            cur.execute("INSERT INTO capa_records (component, defect_type, action_required, batch_id) VALUES (%s, %s, %s, %s)", c)

        for s in ["09:00", "10:00", "11:00", "14:00", "15:00"]:
            cur.execute("INSERT INTO appointments (slot_time, is_booked) VALUES (%s, FALSE)", (s,))

        print("✅ Database Populated Successfully!")
        cur.close()
        conn.close()

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    run_setup()