# tests/test_logic.py
import pytest
from datetime import date
from src.models import Property, Unit, Resident, Occupancy, Rent, UnitStatus
from src.logic import generate_rent_roll, calculate_kpis

# The 'db_session' fixture ensures a clean database state for every test.

# --- Helper function for setting up test data ---
def setup_property_unit_resident(db_session, prop_name="T1", unit_num="U1", res_name="R1"):
    prop = Property(name=prop_name)
    unit = Unit(property=prop, unit_number=unit_num)
    res = Resident(first_name=res_name, last_name="Test")
    db_session.add_all([prop, unit, res])
    db_session.commit()
    return prop, unit, res

# --- Testing generate_rent_roll ---

def test_logic_rent_roll_basic_occupancy(db_session):
    """Test a simple 3-day occupancy period."""
    prop, unit, res = setup_property_unit_resident(db_session)
    
    # Occupancy: Jan 1 to Jan 3 (inclusive) at $1000
    occ = Occupancy(resident=res, unit=unit, move_in_date=date(2024, 1, 1))
    rent = Rent(occupancy=occ, amount=1000, effective_date=date(2024, 1, 1))
    db_session.add_all([occ, rent])
    db_session.commit()
    
    # Run logic directly
    report = generate_rent_roll(prop.id, date(2023, 12, 31), date(2024, 1, 3))
    
    assert len(report) == 4 # Dec 31, Jan 1, Jan 2, Jan 3
    
    # Dec 31: Vacant
    assert report[0]['date'] == "2023-12-31"
    assert report[0]['monthly_rent'] == 0
    assert report[0]['resident_id'] is None

    # Jan 1: Occupied, $1000
    assert report[1]['date'] == "2024-01-01"
    assert report[1]['monthly_rent'] == 1000
    assert report[1]['resident_id'] == res.id

    # Jan 3: Still Occupied, $1000
    assert report[3]['date'] == "2024-01-03"
    assert report[3]['monthly_rent'] == 1000

def test_logic_rent_roll_with_move_out(db_session):
    """Test period crossing a move-out date."""
    prop, unit, res = setup_property_unit_resident(db_session)
    
    # Occupancy: Jan 1 to Jan 2 (Move out on Jan 2)
    occ = Occupancy(resident=res, unit=unit, move_in_date=date(2024, 1, 1), 
                    move_out_date=date(2024, 1, 2))
    rent = Rent(occupancy=occ, amount=2000, effective_date=date(2024, 1, 1))
    db_session.add_all([occ, rent])
    db_session.commit()
    
    report = generate_rent_roll(prop.id, date(2024, 1, 1), date(2024, 1, 3))
    
    # Jan 1: Occupied
    assert report[0]['date'] == "2024-01-01"
    assert report[0]['monthly_rent'] == 2000
    
    # Jan 2: VACANT (Move-out date is Jan 2, rent stops the day *before* the move-out date)
    assert report[1]['date'] == "2024-01-02"
    assert report[1]['monthly_rent'] == 0
    assert report[1]['resident_id'] is None
    
    # Jan 3: Vacant
    assert report[2]['date'] == "2024-01-03"
    assert report[2]['monthly_rent'] == 0

def test_logic_rent_roll_with_rent_change(db_session):
    """Test that the correct historical rent is applied."""
    prop, unit, res = setup_property_unit_resident(db_session)
    
    occ = Occupancy(resident=res, unit=unit, move_in_date=date(2024, 1, 1))
    rent1 = Rent(occupancy=occ, amount=1000, effective_date=date(2024, 1, 1))
    rent2 = Rent(occupancy=occ, amount=1500, effective_date=date(2024, 1, 15))
    db_session.add_all([occ, rent1, rent2])
    db_session.commit()
    
    report = generate_rent_roll(prop.id, date(2024, 1, 14), date(2024, 1, 16))
    
    # Jan 14: Before change, rent is $1000
    assert report[0]['date'] == "2024-01-14"
    assert report[0]['monthly_rent'] == 1000
    
    # Jan 15: On effective date, rent is $1500
    assert report[1]['date'] == "2024-01-15"
    assert report[1]['monthly_rent'] == 1500

    # Jan 16: After change, rent is $1500
    assert report[2]['date'] == "2024-01-16"
    assert report[2]['monthly_rent'] == 1500

def test_logic_rent_roll_unit_status(db_session):
    """Test Unit Status (inactive) overrides occupancy/rent."""
    prop, unit, res = setup_property_unit_resident(db_session)
    
    # Unit is occupied at $1000 from Jan 1
    occ = Occupancy(resident=res, unit=unit, move_in_date=date(2024, 1, 1))
    rent = Rent(occupancy=occ, amount=1000, effective_date=date(2024, 1, 1))
    
    # Unit status change: INACTIVE on Jan 2
    status = UnitStatus(unit=unit, status='inactive', start_date=date(2024, 1, 2))
    
    db_session.add_all([occ, rent, status])
    db_session.commit()
    
    report = generate_rent_roll(prop.id, date(2024, 1, 1), date(2024, 1, 3))
    
    # Jan 1: Active, Occupied, $1000
    assert report[0]['date'] == "2024-01-01"
    assert report[0]['monthly_rent'] == 1000
    assert report[0]['unit_status'] == 'active'

    # Jan 2: Inactive, $0 rent, No resident info
    assert report[1]['date'] == "2024-01-02"
    assert report[1]['monthly_rent'] == 0
    assert report[1]['unit_status'] == 'inactive'
    assert report[1]['resident_id'] is None # Data is suppressed for reporting

def test_logic_kpi_calculation(db_session):
    """Test the calculation of move-ins/outs and occupancy rate."""
    prop, unit1, res1 = setup_property_unit_resident(db_session, unit_num="U1", res_name="R1")
    unit2 = Unit(property=prop, unit_number="U2")
    res2 = Resident(first_name="R2", last_name="Test")
    db_session.add_all([unit2, res2])
    db_session.commit()
    
    # Unit 1: Occupied for all 30 days of June
    occ1 = Occupancy(resident=res1, unit=unit1, move_in_date=date(2024, 6, 1))
    rent1 = Rent(occupancy=occ1, amount=100, effective_date=date(2024, 6, 1))
    
    # Unit 2: Moves in June 16 (15 days occupied: 16th to 30th)
    occ2 = Occupancy(resident=res2, unit=unit2, move_in_date=date(2024, 6, 16))
    rent2 = Rent(occupancy=occ2, amount=100, effective_date=date(2024, 6, 16))
    
    # Unit 1: Moves out June 15
    occ1.move_out_date = date(2024, 6, 15)
    
    db_session.add_all([occ1, rent1, occ2, rent2])
    db_session.commit()

    # Run KPI logic (June 1 - June 30 is 30 days)
    kpis = calculate_kpis(prop.id, date(2024, 6, 1), date(2024, 6, 30))
    
    june_kpis = kpis['2024-06']
    
    # Total Days = 2 Units * 30 Days = 60
    assert june_kpis['total_units_days'] == 60
    
    # Occupied Days:
    # Unit 1: Occupied for 14 days (June 1 to 14) -> 14 days
    # Unit 2: Occupied for 15 days (June 16 to 30) -> 15 days
    # Total Occupied Days = 14 + 15 = 29
    assert june_kpis['occupied_days'] == 29
    
    # Occupancy Rate = 29 / 60 ≈ 0.4833
    assert abs(june_kpis['occupancy_rate'] - 0.4833) < 0.0001

    # Movements:
    # Unit 1: Move out on June 15 (Transition from occupied to vacant on June 15) -> 1 Move Out
    # Unit 2: Move in on June 16 (Transition from vacant to occupied on June 16) -> 1 Move In
    assert june_kpis['move_ins'] == 1
    assert june_kpis['move_outs'] == 1