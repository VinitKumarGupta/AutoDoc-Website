import psycopg2
import json
import random
from datetime import datetime, timedelta

# Import hashing
try:
    from database import hash_password
except ImportError:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    def hash_password(plain): return pwd_context.hash(plain)

# DB CONFIG
DB_CONFIG = {
    "dbname": "fleet_management_v3", 
    "user": "postgres",
    "password": "Prerita#12", 
    "host": "localhost",
    "port": "5432"
}

# SQL SCHEMA
SQL_SETUP = [
    """CREATE EXTENSION IF NOT EXISTS "pgcrypto";""",
    """DROP TABLE IF EXISTS telemetry_stream CASCADE;""",
    """DROP TABLE IF EXISTS maintenance_history CASCADE;""",
    """DROP TABLE IF EXISTS capa_records CASCADE;""",
    """DROP TABLE IF EXISTS appointments CASCADE;""",
    """DROP TABLE IF EXISTS vehicles CASCADE;""",
    """DROP TABLE IF EXISTS dealers CASCADE;""",
    """DROP TABLE IF EXISTS users CASCADE;""",
    
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
    
    # ... (Keeping other tables simple for brevity, assumed standard) ...
    """CREATE TABLE telemetry_stream (event_id BIGSERIAL PRIMARY KEY, chassis_number VARCHAR(50), timestamp TIMESTAMP, speed_kmh DECIMAL, sensor_data JSONB);""",
    """CREATE TABLE maintenance_history (history_id SERIAL PRIMARY KEY, chassis_number VARCHAR(50), service_date DATE, service_type VARCHAR(100), description TEXT, cost DECIMAL);""",
    """CREATE TABLE capa_records (capa_id SERIAL PRIMARY KEY, component VARCHAR(100), defect_type VARCHAR(100), action_required TEXT, batch_id VARCHAR(50));""",
    """CREATE TABLE appointments (appt_id SERIAL PRIMARY KEY, slot_time VARCHAR(20), is_booked BOOLEAN DEFAULT FALSE, booked_chassis VARCHAR(50));"""
]

# SEED DATA
# 1. Dealer (HERO_DLR / admin)
DEALER_USER = ("HERO_DLR", "Hero MotoCorp Delhi", "ADMIN", "hero@auto.local", hash_password("admin"), "8391821234")

# 2. Owner (rahul / 123)
OWNER_USER = ("rahul", "Rahul Sharma", "OWNER", "rahul@gmail.com", hash_password("123"), "9876543210")

VEHICLES = [
    # Unassigned Stock
    {"chassis": "VIN-10001-XA", "make": "Hero", "model": "Splendor Plus", "cat": "2W", "fuel": "PETROL", "owner": None},
    {"chassis": "VIN-10004-XD", "make": "Mahindra", "model": "Blazo", "cat": "HV", "fuel": "DIESEL", "owner": None},
    # Assigned to Rahul
    {"chassis": "VIN-10002-XB", "make": "Hero", "model": "Vida Nex 3", "cat": "EV", "fuel": "EV", "owner": "rahul"},
]

def run_setup():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        cur = conn.cursor()
        print("🚀 Setting up DB...")

        for sql in SQL_SETUP: cur.execute(sql)

        # 1. Create Dealer
        cur.execute("INSERT INTO users (username, full_name, role, email, password_hash, phone) VALUES (%s, %s, %s, %s, %s, %s)", DEALER_USER)
        cur.execute("SELECT user_id FROM users WHERE username=%s", (DEALER_USER[0],))
        dealer_user_id = cur.fetchone()[0]
        cur.execute("INSERT INTO dealers (user_id, location, contact) VALUES (%s, 'Delhi', '8391821234')", (dealer_user_id,))
        cur.execute("SELECT dealer_id FROM dealers WHERE user_id=%s", (dealer_user_id,))
        dealer_id = cur.fetchone()[0]

        # 2. Create Owner (Rahul)
        cur.execute("INSERT INTO users (username, full_name, role, email, password_hash, phone) VALUES (%s, %s, %s, %s, %s, %s)", OWNER_USER)
        cur.execute("SELECT user_id FROM users WHERE username=%s", (OWNER_USER[0],))
        rahul_id = cur.fetchone()[0]

        # 3. Vehicles
        for v in VEHICLES:
            owner_uuid = rahul_id if v["owner"] == "rahul" else None
            sale_date = "NOW()" if owner_uuid else "NULL"
            cur.execute(f"""
                INSERT INTO vehicles (chassis_number, dealer_id, owner_id, make, model, category, fuel_type, manufacturing_year, sale_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 2024, {sale_date})
            """, (v["chassis"], dealer_id, owner_uuid, v["make"], v["model"], v["cat"], v["fuel"]))

        # 4. History/Slots
        cur.execute("INSERT INTO maintenance_history (chassis_number, service_date, service_type, description, cost) VALUES (%s, '2024-01-15', 'Checkup', 'Routine', 500)", ("VIN-10002-XB",))
        for s in ["09:00", "10:00", "14:00"]: cur.execute("INSERT INTO appointments (slot_time) VALUES (%s)", (s,))

        print("✅ Database Reset!")
        conn.close()
    except Exception as e: print(e)

if __name__ == "__main__":
    run_setup()