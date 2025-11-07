# src/services/rent_roll.py
from ..models import Property, Unit, Occupancy
from datetime import timedelta, date


def generate_rent_roll(property_id, start_date, end_date):
    """
    Generates the daily rent roll report for a given property and date range.
    Returns a list of dicts with keys: date, property_id, unit_id, unit_number,
    resident_id, resident_name, monthly_rent, unit_status
    """
    rent_roll_report = []
    prop = Property.query.get(property_id)
    if not prop:
        return []

    all_units = prop.units.all()

    current_date = start_date
    while current_date <= end_date:

        for unit in all_units:

            # 1. Get Unit Status
            unit_status = unit.get_status_on_date(current_date)

            # 2. Find Occupancy
            current_occupancy = unit.occupancies.filter(
                Occupancy.move_in_date <= current_date,
                (Occupancy.move_out_date == None) | (Occupancy.move_out_date > current_date)
            ).first()

            # 3. Compile Snapshot
            if unit_status == 'inactive':
                record = {
                    "resident_id": None, "resident_name": None, "monthly_rent": 0,
                    "unit_status": "inactive"
                }
            elif current_occupancy:
                # Unit is ACTIVE and OCCUPIED
                resident = current_occupancy.resident
                rent_amount = current_occupancy.get_rent_on_date(current_date)
                record = {
                    "resident_id": resident.id,
                    "resident_name": resident.full_name,
                    "monthly_rent": rent_amount,
                    "unit_status": "active"
                }
            else:
                # Unit is ACTIVE and VACANT
                record = {
                    "resident_id": None, "resident_name": None, "monthly_rent": 0,
                    "unit_status": "active"
                }

            composed_unit_number = f"P{prop.id}-{unit.unit_number}"
            rent_roll_report.append({
                "date": current_date.isoformat(),
                "property_id": prop.id,
                "unit_id": unit.id,
                "unit_number": composed_unit_number,
                "resident_id": record.get('resident_id'),
                "resident_name": record.get('resident_name'),
                "monthly_rent": record.get('monthly_rent'),
                "unit_status": record.get('unit_status')
            })

        current_date += timedelta(days=1)

    return rent_roll_report
