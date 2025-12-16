import os
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta

from dotenv import load_dotenv
from passlib.context import CryptContext
from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    create_engine,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.types import CHAR, TypeDecorator


load_dotenv()

# --- CONFIGURATION: LOCAL POSTGRES ---
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:Prerita#12@localhost:5432/fleet_management_v3",
)

engine = create_engine(DATABASE_URL, future=True, echo=False)
SessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
)
Base = declarative_base()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class GUID(TypeDecorator):
    """Platform-independent UUID stored as native UUID or char(36)."""

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import UUID as PGUUID

            return dialect.type_descriptor(PGUUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            try:
                value = uuid.UUID(str(value))
            except ValueError:
                return None
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            value = uuid.UUID(value)
        return value


class User(Base):
    __tablename__ = "users"

    user_id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False)
    email = Column(String(100), unique=True, nullable=True)
    password_hash = Column(Text, nullable=False)
    phone = Column(String(20)) # Added to match populate_data.py
    created_at = Column(DateTime, server_default=func.now())

    dealer = relationship("Dealer", back_populates="user", uselist=False)
    vehicles = relationship(
        "Vehicle", back_populates="owner", foreign_keys="Vehicle.owner_id"
    )


class Dealer(Base):
    __tablename__ = "dealers"

    dealer_id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.user_id", ondelete="CASCADE"), unique=True)
    location = Column(String(100))
    contact = Column(String(30))

    user = relationship("User", back_populates="dealer")
    vehicles = relationship(
        "Vehicle", back_populates="dealer", foreign_keys="Vehicle.dealer_id"
    )


class Vehicle(Base):
    __tablename__ = "vehicles"

    chassis_number = Column(String(50), primary_key=True)
    dealer_id = Column(GUID(), ForeignKey("dealers.dealer_id", ondelete="SET NULL"))
    owner_id = Column(GUID(), ForeignKey("users.user_id", ondelete="SET NULL"))
    category = Column(String(20))
    make = Column(String(50))
    model = Column(String(50))
    manufacturing_year = Column(Integer)
    is_active = Column(Boolean, default=True)
    sale_date = Column(DateTime)
    last_service_date = Column(DateTime)
    fuel_type = Column(String(20)) # Added to match populate_data.py

    dealer = relationship("Dealer", back_populates="vehicles")
    owner = relationship("User", back_populates="vehicles", foreign_keys=[owner_id])


class SensorThreshold(Base):
    __tablename__ = "sensor_thresholds"

    rule_id = Column(Integer, primary_key=True, autoincrement=True)
    vehicle_category = Column(String(20))
    parameter_name = Column(String(50))
    min_val = Column(Numeric(10, 2))
    max_val = Column(Numeric(10, 2))
    unit = Column(String(10))
    severity_level = Column(String(10))


class TelemetryStream(Base):
    __tablename__ = "telemetry_stream"

    event_id = Column(BigInteger, primary_key=True, autoincrement=True)
    chassis_number = Column(String(50), ForeignKey("vehicles.chassis_number", ondelete="CASCADE"))
    timestamp = Column(DateTime, server_default=func.now())
    latitude = Column(Numeric(9, 6))
    longitude = Column(Numeric(9, 6))
    speed_kmh = Column(Numeric(5, 2))
    sensor_data = Column(JSONB().with_variant(JSON, "sqlite"))


class MaintenanceIncident(Base):
    __tablename__ = "maintenance_incidents"

    incident_id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    chassis_number = Column(String(50), ForeignKey("vehicles.chassis_number", ondelete="CASCADE"))
    detected_at = Column(DateTime, default=datetime.utcnow)
    failure_type = Column(String(100))
    root_cause = Column(Text)
    recommended_action = Column(Text)
    status = Column(String(20))
    service_appointment_id = Column(GUID(), nullable=True)


class ServiceBooking(Base):
    __tablename__ = "service_bookings" 
    
    booking_id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(String(30), unique=True, nullable=False)
    chassis_number = Column(String(50), ForeignKey("vehicles.chassis_number", ondelete="CASCADE"))
    owner_id = Column(GUID(), ForeignKey("users.user_id", ondelete="SET NULL"))
    dealer_id = Column(GUID(), ForeignKey("dealers.dealer_id", ondelete="SET NULL"))
    service_center_id = Column(String(50), nullable=True)
    service_center_name = Column(String(100), nullable=True)
    issue = Column(Text)
    status = Column(String(20), default="OPEN")
    created_at = Column(DateTime, default=datetime.utcnow)

    vehicle = relationship("Vehicle")
    owner = relationship("User")
    dealer = relationship("Dealer")

class Appointment(Base):
    __tablename__ = "appointments"
    appt_id = Column(Integer, primary_key=True, autoincrement=True)
    slot_time = Column(String(20))
    is_booked = Column(Boolean, default=False)
    booked_chassis = Column(String(50))


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    if not hashed:
        return False
    try:
        return pwd_context.verify(plain, hashed)
    except ValueError:
        return False


@contextmanager
def session_scope():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db():
    Base.metadata.create_all(bind=engine)

# Keep the _ensure functions for manual usage if needed, 
# though populate_data.py mostly handles seeding now.
def _ensure_user(session, username, full_name, role, email, password, phone):
    user = session.query(User).filter(User.username == username).one_or_none()
    if user: return user
    new_user = User(
        username=username, full_name=full_name, role=role, email=email,
        password_hash=hash_password(password), phone=phone
    )
    session.add(new_user)
    session.flush()
    return new_user

def ensure_seed_data():
    pass 

__all__ = [
    "Base", "Dealer", "MaintenanceIncident", "ServiceBooking", "SessionLocal",
    "TelemetryStream", "User", "Vehicle", "ensure_seed_data", "hash_password",
    "init_db", "session_scope", "verify_password", "Appointment"
]