-- CREATE DATABASE fleet_management_v3;
-- \c fleet_management_v3

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ==========================================
-- CLEANUP: Drop existing tables to prevent Schema Mismatches
-- ==========================================
DROP TABLE IF EXISTS service_bookings CASCADE;
DROP TABLE IF EXISTS telemetry_stream CASCADE;
DROP TABLE IF EXISTS vehicles CASCADE;
DROP TABLE IF EXISTS dealers CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TYPE IF EXISTS vehicle_type_enum CASCADE;
DROP TYPE IF EXISTS fuel_type_enum CASCADE;

-- ==========================================
-- 0. Enums (Strict Typing)
-- ==========================================
DO $$ BEGIN
    CREATE TYPE vehicle_type_enum AS ENUM ('2W', '3W', '4W', 'HV');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE fuel_type_enum AS ENUM ('PETROL', 'DIESEL', 'EV', 'CNG');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- ==========================================
-- 1. Users Table
-- ==========================================
CREATE TABLE IF NOT EXISTS users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    role VARCHAR(20) CHECK (role IN ('OWNER', 'FLEET_MGR', 'MECHANIC', 'ADMIN', 'EMPLOYEE')),
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ==========================================
-- 2. Dealers Table
-- ==========================================
CREATE TABLE IF NOT EXISTS dealers (
    dealer_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
    location VARCHAR(100),
    contact VARCHAR(30)
);

-- ==========================================
-- 3. Vehicles Table (Major Refactor)
-- PK is now chassis_number
-- ==========================================
CREATE TABLE IF NOT EXISTS vehicles (
    chassis_number VARCHAR(50) PRIMARY KEY, -- Unique Chassis Number
    vehicle_number VARCHAR(20),             -- License Plate (assigned on sale)
    
    dealer_id UUID REFERENCES dealers(dealer_id) ON DELETE SET NULL,
    owner_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
    
    -- "Company Car" Logic: List of User IDs allowed to operate this vehicle
    authorized_operators UUID[], 

    make VARCHAR(50) CHECK (make IN ('Hero MotoCorp', 'Mahindra & Mahindra')),
    model VARCHAR(50),
    type vehicle_type_enum NOT NULL,
    fuel_type fuel_type_enum NOT NULL,
    
    manufacturing_year INT,
    is_active BOOLEAN DEFAULT TRUE,
    sale_date TIMESTAMP
);

-- ==========================================
-- 4. Telemetry Stream
-- Uses chassis_number as FK
-- ==========================================
CREATE TABLE IF NOT EXISTS telemetry_stream (
    event_id BIGSERIAL PRIMARY KEY,
    chassis_number VARCHAR(50) REFERENCES vehicles(chassis_number) ON DELETE CASCADE,
    timestamp TIMESTAMP DEFAULT NOW(),
    latitude DECIMAL(9, 6),
    longitude DECIMAL(9, 6),
    speed_kmh DECIMAL(5, 2),
    sensor_data JSONB 
    -- JSON structure will now be: 
    -- { "parameter_name": { "sensor_1": val, "sensor_2": val } }
);

CREATE INDEX IF NOT EXISTS idx_telemetry_chassis ON telemetry_stream (chassis_number, timestamp DESC);

-- ==========================================
-- 5. Service Bookings
-- ==========================================
CREATE TABLE IF NOT EXISTS service_bookings (
    booking_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id VARCHAR(30) UNIQUE NOT NULL, -- e.g., TKT-2024-8899
    chassis_number VARCHAR(50) REFERENCES vehicles(chassis_number) ON DELETE CASCADE,
    owner_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
    dealer_id UUID REFERENCES dealers(dealer_id) ON DELETE SET NULL,
    issue TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'OPEN'
);

-- ==========================================
-- SEED DATA (Hero & Mahindra Only)
-- ==========================================

-- 1. Create Dealers
INSERT INTO users (username, full_name, role, email, password_hash) VALUES
('HERO_DLR', 'Hero MotoCorp Delhi', 'ADMIN', 'hero@auto.local', crypt('admin', gen_salt('bf'))),
('MAHI_DLR', 'Mahindra Rise Mumbai', 'ADMIN', 'mahi@auto.local', crypt('admin', gen_salt('bf')))
ON CONFLICT DO NOTHING;

INSERT INTO dealers (user_id, location, contact)
SELECT user_id, 'New Delhi', '1800-HERO' FROM users WHERE username = 'HERO_DLR'
ON CONFLICT DO NOTHING;

INSERT INTO dealers (user_id, location, contact)
SELECT user_id, 'Mumbai', '1800-MAHI' FROM users WHERE username = 'MAHI_DLR'
ON CONFLICT DO NOTHING;

-- 2. Create Inventory (Chassis Numbers)
DO $$
DECLARE
    hero_id UUID;
    mahi_id UUID;
BEGIN
    SELECT dealer_id INTO hero_id FROM dealers d JOIN users u ON d.user_id = u.user_id WHERE u.username = 'HERO_DLR';
    SELECT dealer_id INTO mahi_id FROM dealers d JOIN users u ON d.user_id = u.user_id WHERE u.username = 'MAHI_DLR';

    -- Hero Splendor+ (2W, Petrol)
    INSERT INTO vehicles (chassis_number, dealer_id, make, model, type, fuel_type, manufacturing_year)
    VALUES ('HERO-SPL-001', hero_id, 'Hero MotoCorp', 'Splendor Plus', '2W', 'PETROL', 2024);

    -- Hero Vida V1 (2W, EV)
    INSERT INTO vehicles (chassis_number, dealer_id, make, model, type, fuel_type, manufacturing_year)
    VALUES ('HERO-VID-002', hero_id, 'Hero MotoCorp', 'Vida V1', '2W', 'EV', 2024);

    -- Mahindra Thar (4W, Diesel)
    INSERT INTO vehicles (chassis_number, dealer_id, make, model, type, fuel_type, manufacturing_year)
    VALUES ('MAHI-THR-001', mahi_id, 'Mahindra & Mahindra', 'Thar', '4W', 'DIESEL', 2023);

    -- Mahindra Treo (3W, EV)
    INSERT INTO vehicles (chassis_number, dealer_id, make, model, type, fuel_type, manufacturing_year)
    VALUES ('MAHI-TRE-001', mahi_id, 'Mahindra & Mahindra', 'Treo', '3W', 'EV', 2023);
    
    -- Mahindra Blazo (HV, Diesel)
    INSERT INTO vehicles (chassis_number, dealer_id, make, model, type, fuel_type, manufacturing_year)
    VALUES ('MAHI-BLZ-999', mahi_id, 'Mahindra & Mahindra', 'Blazo', 'HV', 'DIESEL', 2022);

END $$;