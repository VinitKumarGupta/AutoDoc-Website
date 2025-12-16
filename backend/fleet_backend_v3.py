import datetime
import random
import uuid
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, Integer, Boolean, DateTime, Numeric, Text, ForeignKey, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# ==========================================
# CONFIGURATION
# ==========================================

DATABASE_URL = "postgresql://postgres:Prerita#12@localhost:5432/fleet_management_v3"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
app = FastAPI(title="Fleet Management V3 - Robust Telemetry")

# ==========================================
# SQLALCHEMY MODELS
# ==========================================

class VehicleDB(Base):
    __tablename__ = "vehicles"
    chassis_number = Column(String, primary_key=True)
    vehicle_number = Column(String, nullable=True)
    dealer_id = Column(UUID, ForeignKey("dealers.dealer_id"))
    owner_id = Column(UUID, ForeignKey("users.user_id"))
    make = Column(String)
    model = Column(String)
    type = Column(String) 
    fuel_type = Column(String) 
    authorized_operators = Column(ARRAY(UUID))
    is_active = Column(Boolean, default=True)

class DealerDB(Base):
    __tablename__ = "dealers"
    dealer_id = Column(UUID, primary_key=True)
    contact = Column(String)

class TelemetryDB(Base):
    __tablename__ = "telemetry_stream"
    event_id = Column(Integer, primary_key=True)
    chassis_number = Column(String, ForeignKey("vehicles.chassis_number"))
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    latitude = Column(Numeric(9, 6))
    longitude = Column(Numeric(9, 6))
    speed_kmh = Column(Numeric(5, 2))
    sensor_data = Column(JSONB)

class ServiceBookingDB(Base):
    __tablename__ = "service_bookings"
    booking_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    ticket_id = Column(String, unique=True)
    chassis_number = Column(String, ForeignKey("vehicles.chassis_number"))
    dealer_id = Column(UUID, ForeignKey("dealers.dealer_id"))
    issue = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String, default='OPEN')

# ==========================================
# SCHEMAS
# ==========================================

class ServiceBookingRequest(BaseModel):
    chassis_number: str
    issue: str

class ServiceBookingResponse(BaseModel):
    ticket_id: str
    message: str
    dealer_notified: str

# ==========================================
# UTILITIES
# ==========================================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def generate_redundant_reading(base_value, noise_level=0.05):
    """Generates two sensor readings that are close but slightly different."""
    s1 = base_value + random.uniform(-noise_level, noise_level)
    s2 = base_value + random.uniform(-noise_level, noise_level)
    return {"sensor_1": round(s1, 2), "sensor_2": round(s2, 2)}

# ==========================================
# ENDPOINTS
# ==========================================

@app.get("/")
def read_root():
    return {"status": "V3 System Operational", "mode": "Redundant Sensor Tracking"}

@app.post("/simulate/telemetry/{chassis_number}")
def generate_v3_telemetry(chassis_number: str, count: int = 10, db: Session = Depends(get_db)):
    """
    Generates telemetry based strictly on Fuel Type and Vehicle Type rules.
    """
    vehicle = db.query(VehicleDB).filter(VehicleDB.chassis_number == chassis_number).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    generated_data = []
    base_lat, base_lon = 19.0760, 72.8777
    
    for i in range(count):
        # 1. Base Motion
        speed = random.uniform(0, 100)
        
        # 2. Sensor Packet Construction
        packet = {}
        
        # --- GLOBAL SENSORS (All Vehicles) ---
        packet['bracket_vibration'] = generate_redundant_reading(random.uniform(0.1, 2.5))
        packet['brake_pad_wear'] = generate_redundant_reading(random.uniform(80, 100))

        # --- FUEL SPECIFIC SENSORS ---
        if vehicle.fuel_type == 'EV':
            packet['cell_voltage_delta'] = generate_redundant_reading(random.uniform(0.01, 0.15))
            packet['pack_insulation_resistance'] = generate_redundant_reading(random.uniform(10, 50)) 
            
        elif vehicle.fuel_type in ['PETROL', 'DIESEL']:
            packet['air_fuel_ratio'] = generate_redundant_reading(14.7, noise_level=0.5)
            
        elif vehicle.fuel_type == 'CNG':
            packet['methane_level_ppm'] = generate_redundant_reading(random.uniform(0, 50))
            packet['air_fuel_ratio'] = generate_redundant_reading(14.7, noise_level=0.5)

        # --- HEAVY VEHICLE / DIESEL SPECIFIC ---
        if vehicle.type == 'HV' or vehicle.fuel_type == 'DIESEL':
            packet['filter_delta_p'] = generate_redundant_reading(random.uniform(0.5, 4.0))

        # 3. Create Record
        db_record = TelemetryDB(
            chassis_number=chassis_number,
            timestamp=datetime.datetime.utcnow() - datetime.timedelta(minutes=count-i),
            latitude=base_lat + random.uniform(-0.01, 0.01),
            longitude=base_lon + random.uniform(-0.01, 0.01),
            speed_kmh=round(speed, 2),
            sensor_data=packet
        )
        db.add(db_record)
        generated_data.append(packet)

    db.commit()
    
    return {
        "message": f"Generated {count} V3 packets for {vehicle.model}",
        "fuel_type": vehicle.fuel_type,
        "latest_packet": generated_data[-1] if generated_data else {}
    }

@app.post("/book-service", response_model=ServiceBookingResponse)
def book_service(request: ServiceBookingRequest, db: Session = Depends(get_db)):
    """
    Creates a service booking and routes it to the correct dealer.
    Generates a unique Ticket ID (e.g., TKT-2025-XXXX).
    """
    # 1. Find the vehicle and its dealer
    vehicle = db.query(VehicleDB).filter(VehicleDB.chassis_number == request.chassis_number).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    if not vehicle.dealer_id:
        raise HTTPException(status_code=400, detail="Vehicle has no associated dealer")

    dealer = db.query(DealerDB).filter(DealerDB.dealer_id == vehicle.dealer_id).first()

    # 2. Generate Ticket ID
    year = datetime.datetime.now().year
    rand_suffix = random.randint(1000, 9999)
    ticket_id = f"TKT-{year}-{rand_suffix}"

    # 3. Create Booking
    booking = ServiceBookingDB(
        ticket_id=ticket_id,
        chassis_number=request.chassis_number,
        dealer_id=vehicle.dealer_id,
        issue=request.issue
    )
    db.add(booking)
    db.commit()

    return {
        "ticket_id": ticket_id,
        "message": "Service booked successfully.",
        "dealer_notified": str(dealer.dealer_id) if dealer else "Unknown"
    }

@app.get("/vehicles")
def list_vehicles(db: Session = Depends(get_db)):
    return db.query(VehicleDB).all()