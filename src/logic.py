# src/logic.py (Completed Rent Roll and KPI Logic)
from .models import Property, Unit, Occupancy
from datetime import timedelta, date
from collections import defaultdict

def generate_rent_roll(property_id, start_date, end_date):
    """
    Generates the daily rent roll report for a given property and date range.
    """
    rent_roll_report = []
    prop = Property.query.get(property_id)
    if not prop:
        return []
        
    all_units = prop.units.all()
    
    current_date = start_date
    while current_date <= end_date:
        
        for unit in all_units:
            
            # 1. Get Unit Status (Stretch Goal)
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
                
            # Final record assembly
            rent_roll_report.append({
                "date": current_date.isoformat(),
                "property_id": prop.id,
                "unit_id": unit.id,
                "unit_number": unit.unit_number,
                **record
            })

        current_date += timedelta(days=1)
        
    return rent_roll_report


def calculate_kpis(property_id, start_date, end_date):
    """
    Calculates monthly move-ins, move-outs, and occupancy rates (KPI Stretch Goal).
    """
    
    # 1. Generate Rent Roll Data (Foundation for all KPIs)
    rent_roll = generate_rent_roll(property_id, start_date, end_date)
    
    kpis_by_month = defaultdict(lambda: {
        'total_units_days': 0,
        'occupied_days': 0,
        'move_ins': 0,
        'move_outs': 0,
        'occupancy_rate': 0.0
    })

    # Used to track the state of each unit from the previous day
    # { (unit_id, property_id): resident_id, unit_status }
    previous_state = {} 
    
    # 2. Process Daily Data to Calculate KPIs
    for record in rent_roll:
        dt = date.fromisoformat(record['date'])
        month_key = dt.strftime('%Y-%m')
        key = (record['unit_id'], record['property_id'])
        
        kpi_data = kpis_by_month[month_key]

        # Calculate Occupancy Days
        if record['unit_status'] == 'active':
            kpi_data['total_units_days'] += 1
            if record['resident_id'] is not None:
                kpi_data['occupied_days'] += 1
        
        # Calculate Movements (Move-ins/Move-outs)
        prev_resident_id = previous_state.get(key, {}).get('resident_id')
        
        if record['resident_id'] and prev_resident_id is None:
            # Transition from Vacant to Occupied
            kpi_data['move_ins'] += 1
        elif record['resident_id'] is None and prev_resident_id:
            # Transition from Occupied to Vacant
            kpi_data['move_outs'] += 1
            
        # Update previous state for the next day's comparison
        previous_state[key] = {
            'resident_id': record['resident_id'],
            'unit_status': record['unit_status']
        }

    # 3. Final Calculation (Occupancy Rate)
    final_kpis = {}
    for month, data in kpis_by_month.items():
        data['occupancy_rate'] = (
            round(data['occupied_days'] / data['total_units_days'], 4)
            if data['total_units_days'] > 0 else 0.0
        )
        final_kpis[month] = data
        
    return final_kpis