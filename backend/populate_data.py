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
    """DROP TABLE IF EXISTS service_bookings CASCADE;""",
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
        contact VARCHAR(30),
        brand VARCHAR(50) -- [NEW] Brand Exclusivity
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
    
    """CREATE TABLE service_bookings (
        booking_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        ticket_id VARCHAR(30) UNIQUE NOT NULL,
        chassis_number VARCHAR(50) REFERENCES vehicles(chassis_number) ON DELETE CASCADE,
        owner_id UUID REFERENCES users(user_id),
        dealer_id UUID REFERENCES dealers(dealer_id),
        service_center_id VARCHAR(50),
        service_center_name VARCHAR(100),
        issue TEXT,
        status VARCHAR(20) DEFAULT 'OPEN',
        created_at TIMESTAMP DEFAULT NOW()
    );""",

    """CREATE TABLE maintenance_history (history_id SERIAL PRIMARY KEY, chassis_number VARCHAR(50), service_date DATE, service_type VARCHAR(100), description TEXT, cost DECIMAL);""",
    """CREATE TABLE capa_records (capa_id SERIAL PRIMARY KEY, component VARCHAR(100), defect_type VARCHAR(100), action_required TEXT, batch_id VARCHAR(50));""",
    """CREATE TABLE appointments (appt_id SERIAL PRIMARY KEY, slot_time VARCHAR(20), is_booked BOOLEAN DEFAULT FALSE, booked_chassis VARCHAR(50));"""
]

# --- SEED DATA ---

# 1. Dealers
DEALERS = [
    # (Username, Name, Role, Email, Pass, Phone, Location, Contact, Brand)
    ("HERO_DLR", "Hero MotoCorp Ltd.", "ADMIN", "hero@auto.local", "admin", "9800011111", "Delhi, NCR", "011-234567", "Hero"),
    ("MAH_DLR", "Mahindra & Mahindra Limited", "ADMIN", "mahindra@auto.local", "admin", "9800022222", "Mumbai, MH", "022-456789", "Mahindra")
]

# 2. Users (Owners)
USERS = [
    ("rahul", "Rahul Sharma", "OWNER", "rahul@gmail.com", "123", "9998887771"),
    ("priya", "Priya Singh", "OWNER", "priya@yahoo.com", "123", "9998887772"),
    ("amit", "Amit Verma", "OWNER", "amit@outlook.com", "123", "9998887773"),
    ("sneha", "Sneha Kapoor", "OWNER", "sneha@gmail.com", "123", "9998887774"),
    ("vikram", "Vikram Malhotra", "OWNER", "vikram@tech.local", "123", "9998887775"),
]

# 3. Vehicles (Chassis, DealerUser, OwnerUser, Model, Category, Fuel)
# Note: Make is inferred from Dealer
VEHICLES = [
    # --- RAHUL'S GARAGE (3 Vehicles: 1 Bike, 2 Cars) ---
    {"chassis": "HERO-SPL-001", "dlr": "HERO_DLR", "owner": "rahul", "model": "Splendor Plus", "cat": "2W", "fuel": "PETROL"},
    {"chassis": "MAH-XUV-101", "dlr": "MAH_DLR", "owner": "rahul",  "model": "XUV700 AX7", "cat": "4W", "fuel": "PETROL"},
    {"chassis": "MAH-BE6-104", "dlr": "MAH_DLR", "owner": "rahul",  "model": "BE 6e", "cat": "EV", "fuel": "EV"},

    # --- PRIYA'S GARAGE (2 Vehicles: 2 Scooters) ---
    {"chassis": "HERO-VID-002", "dlr": "HERO_DLR", "owner": "priya", "model": "Vida V1 Pro", "cat": "EV", "fuel": "EV"},
    {"chassis": "HERO-PLE-005", "dlr": "HERO_DLR", "owner": "priya", "model": "Pleasure Plus", "cat": "2W", "fuel": "PETROL"},

    # --- AMIT'S GARAGE (3 Vehicles: 1 Bike, 2 SUVs) ---
    {"chassis": "HERO-MAV-004", "dlr": "HERO_DLR", "owner": "amit",   "model": "Mavrick 440", "cat": "2W", "fuel": "PETROL"},
    {"chassis": "MAH-XUV-105", "dlr": "MAH_DLR", "owner": "amit",     "model": "XUV 3XO", "cat": "4W", "fuel": "PETROL"},
    {"chassis": "MAH-THAR-107", "dlr": "MAH_DLR", "owner": "amit",    "model": "Thar Earth Edit", "cat": "4W", "fuel": "DIESEL"},

    # --- SNEHA'S GARAGE (2 Vehicles: 1 Off-road, 1 Bike) ---
    {"chassis": "MAH-THR-102", "dlr": "MAH_DLR", "owner": "sneha",  "model": "Thar Roxx", "cat": "4W", "fuel": "DIESEL"},
    {"chassis": "HERO-XPL-003", "dlr": "HERO_DLR", "owner": "sneha", "model": "Xpulse 200", "cat": "2W", "fuel": "PETROL"},

    # --- VIKRAM'S GARAGE (4 Vehicles: Collector!) ---
    {"chassis": "MAH-SCO-103", "dlr": "MAH_DLR", "owner": "vikram", "model": "Scorpio N", "cat": "4W", "fuel": "DIESEL"},
    {"chassis": "MAH-BOL-106", "dlr": "MAH_DLR", "owner": "vikram", "model": "Bolero Neo", "cat": "4W", "fuel": "DIESEL"},
    {"chassis": "HERO-KAR-006", "dlr": "HERO_DLR", "owner": "vikram", "model": "Karizma XMR", "cat": "2W", "fuel": "PETROL"},
    {"chassis": "HERO-VID-009", "dlr": "HERO_DLR", "owner": "vikram", "model": "Vida V1 Plus", "cat": "EV", "fuel": "EV"},

    # --- UNSOLD STOCK (For Dealer Demo) ---
    {"chassis": "HERO-SPL-007", "dlr": "HERO_DLR", "owner": None,   "model": "Splendor Pro", "cat": "2W", "fuel": "PETROL"},
    {"chassis": "HERO-DEST-008", "dlr": "HERO_DLR", "owner": None,  "model": "Destini 125", "cat": "2W", "fuel": "PETROL"},
    {"chassis": "MAH-XUV-108", "dlr": "MAH_DLR", "owner": None,     "model": "XUV 400 EV", "cat": "4W", "fuel": "EV"},
    {"chassis": "MAH-SCN-109", "dlr": "MAH_DLR", "owner": None,     "model": "Scorpio Classic", "cat": "4W", "fuel": "DIESEL"},
]

def run_setup():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        cur = conn.cursor()
        print("🚀 Setting up DB with Rich Data...")

        # 1. Run Schema
        for sql in SQL_SETUP: cur.execute(sql)

        dealer_map = {} # username -> dealer_id
        user_map = {}   # username -> user_id

        # 2. Insert Dealers
        for d in DEALERS:
            # Create User entry for Dealer
            cur.execute(
                "INSERT INTO users (username, full_name, role, email, password_hash, phone) VALUES (%s, %s, %s, %s, %s, %s) RETURNING user_id", 
                (d[0], d[1], d[2], d[3], hash_password(d[4]), d[5])
            )
            u_id = cur.fetchone()[0]
            
            # Create Dealer entry
            cur.execute(
                "INSERT INTO dealers (user_id, location, contact, brand) VALUES (%s, %s, %s, %s) RETURNING dealer_id",
                (u_id, d[6], d[7], d[8])
            )
            d_id = cur.fetchone()[0]
            dealer_map[d[0]] = (d_id, d[8]) # Store ID and Brand
            print(f"✅ Created Dealer: {d[1]} ({d[8]})")

        # 3. Insert Users
        for u in USERS:
            cur.execute(
                "INSERT INTO users (username, full_name, role, email, password_hash, phone) VALUES (%s, %s, %s, %s, %s, %s) RETURNING user_id",
                (u[0], u[1], u[2], u[3], hash_password(u[4]), u[5])
            )
            user_map[u[0]] = cur.fetchone()[0]
            print(f"👤 Created User: {u[1]}")

        # 4. Insert Vehicles
        for v in VEHICLES:
            dlr_id, brand = dealer_map[v["dlr"]]
            own_id = user_map[v["owner"]] if v["owner"] else None
            sale_date = "NOW()" if own_id else "NULL"
            
            # Note: We use the Dealer's brand for the Vehicle Make
            cur.execute(f"""
                INSERT INTO vehicles (chassis_number, dealer_id, owner_id, make, model, category, fuel_type, manufacturing_year, sale_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 2024, {sale_date})
            """, (v["chassis"], dlr_id, own_id, brand, v["model"], v["cat"], v["fuel"]))
        
        print(f"🚗 Added {len(VEHICLES)} Vehicles.")

        # 5. Add some history
        cur.execute("INSERT INTO appointments (slot_time) VALUES ('09:00'), ('10:00'), ('11:00'), ('14:00'), ('15:00')")
        
        print("✅ Database Reset Complete!")
        conn.close()
    except Exception as e: 
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    run_setup()