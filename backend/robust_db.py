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
)


init_db()
ensure_seed_data()


def _serialize_dealer(dealer: Dealer) -> Dict:
    inventory = [
        {"id": v.chassis_number, "model": v.model, "status": "Available"}
        for v in dealer.vehicles
        if v.owner_id is None
    ]
    sold = []
    for v in dealer.vehicles:
        if v.owner is None:
            continue
        sold.append(
            {
                "id": v.chassis_number,
                "model": v.model,
                "owner_name": v.owner.full_name,
                "owner_phone": v.owner.phone,
                "sale_date": (v.sale_date.strftime("%Y-%m-%d") if v.sale_date else None),
            }
        )
    return {
        "id": dealer.user.username,
        "name": dealer.user.full_name,
        "location": dealer.location,
        "contact": dealer.contact,
        "inventory": inventory,
        "sold_vehicles": sold,
    }


def _serialize_user(user: User) -> Dict:
    vehicles = []
    for v in user.vehicles:
        dealer_name = v.dealer.user.full_name if v.dealer and v.dealer.user else "Dealer"
        dealer_location = v.dealer.location if v.dealer else ""
        vehicles.append(
            {
                "id": v.chassis_number,
                "model": v.model,
                "dealer": {"name": dealer_name, "location": dealer_location},
            }
        )
    return {
        "id": str(user.user_id),
        "username": user.username,
        "name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "vehicles": vehicles,
    }


def authenticate_dealer(username: str, password: str) -> Optional[Dict]:
    with session_scope() as session:
        dealer = (
            session.query(Dealer)
            .join(User)
            .options(
                joinedload(Dealer.user),
                joinedload(Dealer.vehicles).joinedload(Vehicle.owner),
            )
            .filter(User.username == username, User.role.in_(["ADMIN", "FLEET_MGR"]))
            .one_or_none()
        )
        if not dealer or not verify_password(password, dealer.user.password_hash):
            return None
        return _serialize_dealer(dealer)


def authenticate_owner(username: str, password: str) -> Optional[Dict]:
    with session_scope() as session:
        user = (
            session.query(User)
            .options(
                joinedload(User.vehicles)
                .joinedload(Vehicle.dealer)
                .joinedload(Dealer.user)
            )
            .filter(User.username == username, User.role == "OWNER")
            .one_or_none()
        )
        if not user or not verify_password(password, user.password_hash):
            return None
        return _serialize_user(user)


def get_dealer_snapshot(username: str) -> Optional[Dict]:
    with session_scope() as session:
        dealer = (
            session.query(Dealer)
            .join(User)
            .options(
                joinedload(Dealer.user),
                joinedload(Dealer.vehicles).joinedload(Vehicle.owner),
            )
            .filter(User.username == username)
            .one_or_none()
        )
        if not dealer:
            return None
        return _serialize_dealer(dealer)


def add_stock(dealer_username: str, chassis_number: str, model: str) -> bool:
    normalized_model = model.strip()
    if not normalized_model:
        return False
    with session_scope() as session:
        dealer = (
            session.query(Dealer)
            .join(User)
            .filter(User.username == dealer_username)
            .one_or_none()
        )
        if not dealer:
            return False
        existing = (
            session.query(Vehicle).filter(Vehicle.chassis_number == chassis_number).one_or_none()
        )
        if existing:
            return False

        make = normalized_model.split()[0]
        vehicle = Vehicle(
            chassis_number=chassis_number,
            dealer_id=dealer.dealer_id,
            model=normalized_model,
            make=make,
            category="EV_PV",
            manufacturing_year=datetime.utcnow().year,
        )
        session.add(vehicle)
        return True


def assign_vehicle(
    dealer_username: str, chassis_number: str, target_username: str
) -> Tuple[bool, str]:
    with session_scope() as session:
        dealer = (
            session.query(Dealer)
            .join(User)
            .filter(User.username == dealer_username)
            .one_or_none()
        )
        if not dealer:
            return False, "Dealer not found"
        vehicle = (
            session.query(Vehicle)
            .filter(Vehicle.chassis_number == chassis_number, Vehicle.dealer_id == dealer.dealer_id)
            .one_or_none()
        )
        if not vehicle:
            return False, "Vehicle not found in stock"
        if vehicle.owner_id:
            return False, "Vehicle already assigned"
        owner = (
            session.query(User)
            .filter(User.username == target_username, User.role == "OWNER")
            .one_or_none()
        )
        if not owner:
            return False, "Target user not found"

        vehicle.owner_id = owner.user_id
        vehicle.sale_date = datetime.utcnow()
        return True, "Success"


def record_service_booking(
    ticket_id: str,
    chassis_number: str,
    owner_name: str,
    issue: str,
    center_id: str,
    center_name: str,
) -> Dict:
    with session_scope() as session:
        vehicle = (
            session.query(Vehicle)
            .options(
                joinedload(Vehicle.dealer).joinedload(Dealer.user),
                joinedload(Vehicle.owner),
            )
            .filter(Vehicle.chassis_number == chassis_number)
            .one_or_none()
        )
        owner = vehicle.owner if vehicle else None
        dealer = vehicle.dealer if vehicle else None

        booking = ServiceBooking(
            ticket_id=ticket_id,
            chassis_number=chassis_number,
            owner_id=owner.user_id if owner else None,
            dealer_id=dealer.dealer_id if dealer else None,
            service_center_id=center_id,
            service_center_name=center_name,
            issue=issue,
        )
        session.add(booking)
        session.flush()

        return {
            "ticket_id": ticket_id,
            "vehicle_id": chassis_number,
            "owner_name": owner_name or (owner.full_name if owner else None),
            "issue": issue,
            "service_center": center_name,
            "center_id": center_id,
            "created_at": booking.created_at.isoformat(),
        }


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
                    "owner_name": b.owner.full_name if b.owner else "",
                    "issue": b.issue,
                    "service_center": b.service_center_name,
                    "center_id": b.service_center_id,
                    "created_at": b.created_at.isoformat(),
                }
            )
        return results