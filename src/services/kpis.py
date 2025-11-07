# src/services/kpis.py
from ..models import Property, Unit, Occupancy
from .. import db
from .rent_roll import generate_rent_roll
from datetime import date
from collections import defaultdict
import calendar


def move_in_out_counts(property_id, start_date, end_date):
    """
    Returns the number of move-ins and move-outs for a property in the given date range.
    """
    occs = Occupancy.query.join(Unit).filter(Unit.property_id == property_id).all()
    move_ins = sum(1 for occ in occs if occ.move_in_date and start_date <= occ.move_in_date <= end_date)
    move_outs = sum(1 for occ in occs if occ.move_out_date and start_date <= occ.move_out_date <= end_date)
    return {'move_ins': move_ins, 'move_outs': move_outs}

def occupancy_rate_for_month(property_id, year, month):
    """
    Returns the occupancy rate for a property for a given calendar month (YYYY, MM).
    """
    prop = db.session.get(Property, property_id)
    if not prop:
        return {'occupancy_rate': 0.0, 'total_units_days': 0, 'occupied_days': 0}
    total_units = prop.units.count()
    days_in_month = calendar.monthrange(year, month)[1]
    month_start = date(year, month, 1)
    month_end = date(year, month, days_in_month)
    rent_roll_month = generate_rent_roll(property_id, month_start, month_end)
    occupied_days = sum(1 for r in rent_roll_month if r.get('resident_id') is not None)
    total_unit_days = total_units * days_in_month if total_units > 0 else 0
    occupancy_rate = round(occupied_days / total_unit_days, 4) if total_unit_days > 0 else 0.0
    return {
        'occupancy_rate': occupancy_rate,
        'total_units_days': total_unit_days,
        'occupied_days': occupied_days,
        'month': f"{year:04d}-{month:02d}"
    }
