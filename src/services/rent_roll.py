# src/services/rent_roll.py
from ..models import Property, Unit, Occupancy
from .. import db
from datetime import timedelta, date


def generate_rent_roll(property_id, start_date, end_date):
    """
    Generates the daily rent roll report for a given property and date range.
    Returns a list of dicts with keys: date, property_id, unit_id, unit_number,
    resident_id, resident_name, monthly_rent, unit_status
    """
    rent_roll_report = []
    prop = db.session.get(Property, property_id)
    if not prop:
        return []

    all_units = prop.units.all()

    current_date = start_date
    while current_date <= end_date:
        for unit in all_units:
            unit_status = unit.get_status_on_date(current_date)
            composed_unit_number = f"P{prop.id}-{unit.unit_number}"
            if unit_status == 'inactive':
                rent_roll_report.append({
                    "date": current_date.isoformat(),
                    "property_id": prop.id,
                    "unit_id": unit.id,
                    "unit_number": composed_unit_number,
                    "resident_id": None,
                    "resident_name": None,
                    "monthly_rent": 0,
                    "unit_status": "inactive"
                })
                continue
            # Find occupancy where move_in_date <= current_date < move_out_date (or move_out_date is None)
            occ = unit.occupancies.filter(
                Occupancy.move_in_date <= current_date,
                (Occupancy.move_out_date == None) | (Occupancy.move_out_date > current_date)
            ).first()
            if occ:
                resident = occ.resident
                # Only emit one record per day per occupancy: latest rent as of that day
                rent_amount = occ.get_rent_on_date(current_date)
                rent_roll_report.append({
                    "date": current_date.isoformat(),
                    "property_id": prop.id,
                    "unit_id": unit.id,
                    "unit_number": composed_unit_number,
                    "resident_id": resident.id,
                    "resident_name": resident.full_name,
                    "monthly_rent": rent_amount,
                    "unit_status": "active"
                })
            else:
                rent_roll_report.append({
                    "date": current_date.isoformat(),
                    "property_id": prop.id,
                    "unit_id": unit.id,
                    "unit_number": composed_unit_number,
                    "resident_id": None,
                    "resident_name": None,
                    "monthly_rent": 0,
                    "unit_status": "active"
                })
        current_date += timedelta(days=1)
    return rent_roll_report
