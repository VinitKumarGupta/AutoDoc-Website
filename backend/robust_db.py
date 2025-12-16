from datetime import datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import joinedload

from database import (
    Dealer,
    ServiceBooking,
    User,
    Vehicle,
    ensure_seed_data,
    init_db,
    session_scope,
    verify_password,
    Appointment
)

# Initialize
init_db()

def _serialize_dealer(dealer: Dealer) -> Dict:
    """
    Helper to format dealer data for the frontend.
    """
    # 1. Get Inventory
    inventory = [
        {"id": v.chassis_number, "chassis_number": v.chassis_number, "model": v.model, "status": "Available"}
        for v in dealer.vehicles
        if v.owner_id is None
    ]
    
    # 2. Get Sold History
    sold = []
    for v in dealer.vehicles:
        if v.owner_id is None:
            continue
        sold.append(
            {
                "id": v.chassis_number,
                "chassis_number": v.chassis_number, # Added for consistency
                "model": v.model,
                "owner_username": v.owner.username if v.owner else "Unknown", 
                "owner_name": v.owner.full_name if v.owner else "Unknown",
                "owner_phone": v.owner.phone if v.owner else "N/A",
                "sale_date": (v.sale_date.strftime("%Y-%m-%d") if v.sale_date else None),
            }
        )
        
    return {
        "id": dealer.user.username, 
        "dealer_id": str(dealer.dealer_id), 
        "name": dealer.user.full_name,
        "location": dealer.location,
        "contact": dealer.contact,
        "inventory": inventory,
        "sold_vehicles": sold,
    }


def authenticate_dealer(username, password) -> Optional[Dict]:
    with session_scope() as session:
        # 1. Find User
        user = session.query(User).filter(User.username == username).first()
        if not user or not verify_password(password, user.password_hash):
            return None
        
        # 2. Ensure Role
        if user.role not in ["ADMIN", "DEALER"]:
            return None

        # 3. Find Dealer Profile
        dealer = session.query(Dealer).filter(Dealer.user_id == user.user_id).options(
            joinedload(Dealer.vehicles).joinedload(Vehicle.owner),
            joinedload(Dealer.user)
        ).first()
        
        if not dealer:
            return None

        return _serialize_dealer(dealer)


def authenticate_owner(username, password) -> Optional[Dict]:
    with session_scope() as session:
        user = session.query(User).filter(User.username == username).first()
        if not user or not verify_password(password, user.password_hash):
            return None

        vehicles = session.query(Vehicle).filter(Vehicle.owner_id == user.user_id).all()
        
        return {
            "user_id": str(user.user_id),
            "username": user.username,
            "full_name": user.full_name, # Mapped to support App.jsx
            "name": user.full_name,
            "vehicles": [
                {
                    "id": v.chassis_number,
                    "chassis_number": v.chassis_number,
                    "model": v.model,
                    "dealer_id": str(v.dealer_id) if v.dealer_id else None,
                    "dealer": {
                        "name": v.dealer.user.full_name if v.dealer and v.dealer.user else "Hero MotoCorp"
                    }
                }
                for v in vehicles
            ],
        }


def add_stock(dealer_id_uuid: str, chassis_number: str, model: str) -> bool:
    """
    Adds a vehicle to a dealer's inventory.
    """
    with session_scope() as session:
        # Check exists
        if session.query(Vehicle).filter_by(chassis_number=chassis_number).first():
            return False
        
        new_vehicle = Vehicle(
            chassis_number=chassis_number,
            dealer_id=dealer_id_uuid, # Uses UUID
            model=model,
            category="4W",
            make="AutoDoc OEM",
            manufacturing_year=2025,
            is_active=True
        )
        session.add(new_vehicle)
        return True


def assign_vehicle(dealer_id_uuid: str, chassis_number: str, target_username: str) -> Tuple[bool, str]:
    """
    Assigns a vehicle from dealer to user.
    """
    with session_scope() as session:
        target = session.query(User).filter_by(username=target_username).first()
        if not target:
            return False, "User not found"

        vehicle = session.query(Vehicle).filter_by(chassis_number=chassis_number, dealer_id=dealer_id_uuid).first()
        if not vehicle:
            return False, "Vehicle not found in your inventory"

        if vehicle.owner_id:
            return False, "Vehicle already owned"

        vehicle.owner_id = target.user_id
        vehicle.sale_date = datetime.utcnow()
        return True, "Vehicle assigned successfully"


def get_dealer_snapshot(dealer_id_uuid: str) -> Optional[Dict]:
    """Refreshes dealer data after an operation."""
    with session_scope() as session:
        dealer = session.query(Dealer).filter(Dealer.dealer_id == dealer_id_uuid).options(
            joinedload(Dealer.vehicles).joinedload(Vehicle.owner),
            joinedload(Dealer.user)
        ).first()
        if not dealer: return None
        return _serialize_dealer(dealer)


def record_service_booking(ticket_id, chassis, owner_name, issue, center_id, center_name):
    with session_scope() as session:
        # Find UUIDs if possible, else store loose references
        vehicle = session.query(Vehicle).filter_by(chassis_number=chassis).first()
        
        booking = ServiceBooking(
            ticket_id=ticket_id,
            chassis_number=chassis,
            owner_id=vehicle.owner_id if vehicle else None,
            dealer_id=vehicle.dealer_id if vehicle else None,
            service_center_id=center_id,
            service_center_name=center_name,
            issue=issue,
        )
        session.add(booking)
        return True


def list_service_bookings(center_id: Optional[str] = None) -> List[Dict]:
    with session_scope() as session:
        query = session.query(ServiceBooking).options(
            joinedload(ServiceBooking.vehicle),
            joinedload(ServiceBooking.owner),
        )
        if center_id:
            query = query.filter(ServiceBooking.service_center_id == center_id)
        
        bookings = query.order_by(ServiceBooking.created_at.desc()).all()

        results = []
        for b in bookings:
            results.append(
                {
                    "ticket_id": b.ticket_id,
                    "vehicle_id": b.chassis_number,
                    "owner_name": b.owner.full_name if b.owner else (b.vehicle.owner.full_name if b.vehicle and b.vehicle.owner else "Unknown"),
                    "issue": b.issue,
                    "service_center": b.service_center_name,
                    "center_id": b.service_center_id,
                    "created_at": b.created_at.isoformat(),
                }
            )
        return results