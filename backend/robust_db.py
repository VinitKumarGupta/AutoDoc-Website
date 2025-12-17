from datetime import datetime
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import joinedload
from database import Dealer, ServiceBooking, User, Vehicle, ensure_seed_data, init_db, session_scope, verify_password

init_db()

def _serialize_dealer(dealer: Dealer) -> Dict:
    # 1. Inventory (Unsold)
    inventory = []
    for v in dealer.vehicles:
        if v.owner_id is None:
            inventory.append({
                "chassis_number": v.chassis_number, # --- FIX: App.jsx needs this key
                "model": v.model,
                "status": "Available"
            })
            
    # 2. Sold History
    sold = []
    for v in dealer.vehicles:
        if v.owner_id:
            sold.append({
                "chassis_number": v.chassis_number, # --- FIX: App.jsx needs this key
                "model": v.model,
                "owner_username": v.owner.username if v.owner else "Unknown",
                "sale_date": str(v.sale_date.date()) if v.sale_date else "N/A"
            })

    return {
        "dealer_id": str(dealer.dealer_id),
        "username": dealer.user.username,
        "full_name": dealer.user.full_name,
        "brand": dealer.brand, # Return brand info
        "inventory": inventory,
        "sold_vehicles": sold,
    }

def _serialize_owner(user: User) -> Dict:
    vehicles = []
    for v in user.vehicles:
        vehicles.append({
            "chassis_number": v.chassis_number, # --- FIX
            "model": v.model,
            "dealer_id": str(v.dealer_id) if v.dealer_id else None
        })
        
    return {
        "user_id": str(user.user_id),
        "username": user.username,
        "full_name": user.full_name, # --- FIX
        "vehicles": vehicles
    }

def authenticate_dealer(username, password) -> Optional[Dict]:
    with session_scope() as session:
        user = session.query(User).filter(User.username == username).first()
        if not user or not verify_password(password, user.password_hash): return None
        
        # [FIX] Enforce Role Check
        if user.role != "ADMIN":  # In populate_data.py, HERO_DLR is 'ADMIN'
            return None
        
        dealer = session.query(Dealer).filter(Dealer.user_id == user.user_id).options(
            joinedload(Dealer.vehicles).joinedload(Vehicle.owner),
            joinedload(Dealer.user)
        ).first()
        
        if not dealer: return None
        return _serialize_dealer(dealer)

def authenticate_owner(username, password) -> Optional[Dict]:
    with session_scope() as session:
        user = session.query(User).filter(User.username == username).first()
        if not user or not verify_password(password, user.password_hash): return None
        
        # [FIX] Enforce Role Check
        if user.role != "OWNER": # In populate_data.py, rahul is 'OWNER'
            return None
        
        # Ensure vehicles are loaded
        session.query(Vehicle).filter(Vehicle.owner_id == user.user_id).all()
        return _serialize_owner(user)

def add_stock(dealer_id_or_user, chassis_number, model):
    with session_scope() as session:
        # Check if vehicle exists
        if session.query(Vehicle).filter_by(chassis_number=chassis_number).first(): 
            return False
        
        # 1. Fetch Dealer to get their Brand
        dealer = session.query(Dealer).filter(Dealer.dealer_id == dealer_id_or_user).first()
        if not dealer:
            return False
            
        # 2. Enforce Brand Exclusivity
        # The vehicle make is FORCED to be the Dealer's brand
        vehicle_make = dealer.brand if dealer.brand else "Generic"
        
        v = Vehicle(
            chassis_number=chassis_number,
            dealer_id=dealer_id_or_user, 
            model=model,
            category="4W", # You might want to make this dynamic later
            make=vehicle_make, # [FIX] No longer hardcoded "AutoDoc"
            manufacturing_year=2025,
            is_active=True
        )
        session.add(v)
        return True

def assign_vehicle(dealer_id, chassis_number, target_username):
    with session_scope() as session:
        target = session.query(User).filter_by(username=target_username).first()
        if not target: return False, "User not found"
        
        v = session.query(Vehicle).filter_by(chassis_number=chassis_number, dealer_id=dealer_id).first()
        if not v: return False, "Vehicle not found"
        
        v.owner_id = target.user_id
        v.sale_date = datetime.utcnow()
        return True, "Assigned"

def get_dealer_snapshot(dealer_id):
    with session_scope() as session:
        dealer = session.query(Dealer).filter(Dealer.dealer_id == dealer_id).first()
        if dealer: return _serialize_dealer(dealer)
        return None

def record_service_booking(ticket_id, chassis, owner_name, issue, center_id, center_name):
    with session_scope() as session:
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

def list_service_bookings(center_id=None):
    with session_scope() as session:
        query = session.query(ServiceBooking).options(joinedload(ServiceBooking.vehicle), joinedload(ServiceBooking.owner))
        if center_id: query = query.filter(ServiceBooking.service_center_id == center_id)
        bookings = query.order_by(ServiceBooking.created_at.desc()).all()
        results = []
        for b in bookings:
            results.append({
                "ticket_id": b.ticket_id,
                "vehicle_id": b.chassis_number,
                "owner_name": b.owner.full_name if b.owner else (b.vehicle.owner.full_name if b.vehicle and b.vehicle.owner else "Unknown"),
                "issue": b.issue,
                "service_center": b.service_center_name,
                "center_id": b.service_center_id,
                "created_at": b.created_at.isoformat(),
            })
        return results