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

@pytest.mark.parametrize("rents, queries", [
    # Single mid-month change
    (
        [(1000, date(2024,1,1)), (1500, date(2024,1,15))],
        [ (date(2024,1,14),1000), (date(2024,1,15),1500), (date(2024,1,16),1500) ]
    ),
    # Multiple changes choose latest effective <= query
    (
        [(1000, date(2024,5,1)), (1200, date(2024,5,15)), (1500, date(2024,6,1))],
        [ (date(2024,5,14),1000), (date(2024,5,15),1200), (date(2024,6,1),1500) ]
    ),
])

def test_rent_history_variants(db_session, rents, queries):
    """Parametrized: various rent history scenarios and expected amounts on query dates."""
    prop, unit, res = setup_property_unit_resident(db_session)
    occ = Occupancy(resident=res, unit=unit, move_in_date=date(2024,1,1))
    db_session.add(occ)
    db_session.commit()

    # create Rent records from rents list (amount, effective_date)
    rent_objs = [ Rent(occupancy=occ, amount=amt, effective_date=eff) for amt, eff in rents ]
    db_session.add_all(rent_objs)
    db_session.commit()

    # Run queries and assert expected rent amounts
    for q_date, expected in queries:
        report = generate_rent_roll(prop.id, q_date, q_date)
        assert report[0]['monthly_rent'] == expected

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
    
    # Unit 1: Occupied before the KPI month so only the move-out happens in June
    occ1 = Occupancy(resident=res1, unit=unit1, move_in_date=date(2024, 5, 1))
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


# ...existing code...

# --- Additional edge-case tests for generate_rent_roll and KPI logic ---

def test_generate_rent_roll_no_units(db_session):
    """A property with no units should produce an empty rent-roll."""
    prop = Property(name="EmptyProp")
    db_session.add(prop)
    db_session.commit()

    report = generate_rent_roll(prop.id, date(2024, 1, 1), date(2024, 1, 3))
    assert report == []


def test_move_in_and_move_out_same_day_results_in_vacant(db_session):
    """
    If an occupancy has the same move_in_date and move_out_date,
    it should not count as occupied on that date (move_out is exclusive).
    """
    prop, unit, res = setup_property_unit_resident(db_session, prop_name="SameDay", unit_num="S1", res_name="SDR")
    occ = Occupancy(resident=res, unit=unit, move_in_date=date(2024, 1, 10), move_out_date=date(2024, 1, 10))
    rent = Rent(occupancy=occ, amount=500, effective_date=date(2024, 1, 10))
    db_session.add_all([occ, rent])
    db_session.commit()

    report = generate_rent_roll(prop.id, date(2024, 1, 10), date(2024, 1, 10))
    assert len(report) == 1
    rec = report[0]
    # Should be treated as vacant on that day
    assert rec['resident_id'] is None
    assert rec['monthly_rent'] == 0


def test_missing_initial_rent_results_in_zero_rent(db_session):
    """
    If an Occupancy exists but no Rent records were created, the rent should be treated as 0.
    (This verifies defensive behavior in get_rent_on_date.)
    """
    prop, unit, res = setup_property_unit_resident(db_session, prop_name="NoRent", unit_num="NR1", res_name="NRR")
    occ = Occupancy(resident=res, unit=unit, move_in_date=date(2024, 2, 1))
    db_session.add(occ)
    db_session.commit()

    report = generate_rent_roll(prop.id, date(2024, 2, 1), date(2024, 2, 1))
    assert report[0]['monthly_rent'] == 0
    assert report[0]['resident_id'] == res.id  # occupancy still reported, but rent is 0


def test_unit_status_on_same_day_as_move_in_suppresses_reporting(db_session):
    """
    If a unit becomes inactive on the same date a resident would move in,
    unit status should take precedence for reports (inactive => suppressed occupant/rent).
    """
    prop, unit, res = setup_property_unit_resident(db_session, prop_name="StatusSameDay", unit_num="US1", res_name="USR")
    occ = Occupancy(resident=res, unit=unit, move_in_date=date(2024, 3, 1))
    rent = Rent(occupancy=occ, amount=800, effective_date=date(2024, 3, 1))
    # Unit is set inactive on the same day
    status = UnitStatus(unit=unit, status='inactive', start_date=date(2024, 3, 1))

    db_session.add_all([occ, rent, status])
    db_session.commit()

    report = generate_rent_roll(prop.id, date(2024, 3, 1), date(2024, 3, 1))
    rec = report[0]
    # Status takes precedence: no resident data and rent = 0
    assert rec['unit_status'] == 'inactive'
    assert rec['resident_id'] is None
    assert rec['monthly_rent'] == 0


def test_kpis_count_moves_on_boundaries(db_session):
    """
    A move-in on the start_date and a move-out on the end_date should be counted
    in the KPI for the respective months (start/end inclusive).
    """
    prop, unit1, res1 = setup_property_unit_resident(db_session, prop_name="BoundaryProp", unit_num="B1", res_name="BR1")
    unit2 = Unit(property=prop, unit_number="B2")
    res2 = Resident(first_name="BR2", last_name="Test")
    db_session.add_all([unit2, res2])
    db_session.commit()

    # Move-in on the first day of the range
    occ_in = Occupancy(resident=res2, unit=unit2, move_in_date=date(2024, 4, 1))
    rent_in = Rent(occupancy=occ_in, amount=100, effective_date=date(2024, 4, 1))

    # Move-out on the last day of the range
    occ_out = Occupancy(resident=res1, unit=unit1, move_in_date=date(2024, 3, 1))
    occ_out.move_out_date = date(2024, 4, 30)
    rent_out = Rent(occupancy=occ_out, amount=200, effective_date=date(2024, 3, 1))

    db_session.add_all([occ_in, rent_in, occ_out, rent_out])
    db_session.commit()

    kpis = calculate_kpis(prop.id, date(2024, 4, 1), date(2024, 4, 30))
    april = kpis['2024-04']

    # Expect one move-in (on Apr 1) and one move-out (on Apr 30)
    assert april['move_ins'] == 1
    assert april['move_outs'] == 1


def test_rent_history_returns_latest_effective_amount(db_session):
    """
    Verify that get_rent_on_date returns the rent with the latest effective_date <= query date.
    """
    prop, unit, res = setup_property_unit_resident(db_session, prop_name="RentHistory", unit_num="RH1", res_name="RHR")
    occ = Occupancy(resident=res, unit=unit, move_in_date=date(2024, 5, 1))
    rent_a = Rent(occupancy=occ, amount=1000, effective_date=date(2024, 5, 1))
    rent_b = Rent(occupancy=occ, amount=1200, effective_date=date(2024, 5, 15))
    rent_c = Rent(occupancy=occ, amount=1500, effective_date=date(2024, 6, 1))
    db_session.add_all([occ, rent_a, rent_b, rent_c])
    db_session.commit()

    # May 14 -> should pick 1000
    report_may14 = generate_rent_roll(prop.id, date(2024, 5, 14), date(2024, 5, 14))[0]
    assert report_may14['monthly_rent'] == 1000

    # May 15 -> should pick 1200 (effective that day)
    report_may15 = generate_rent_roll(prop.id, date(2024, 5, 15), date(2024, 5, 15))[0]
    assert report_may15['monthly_rent'] == 1200

    # Jun 1 -> should pick 1500
    report_jun1 = generate_rent_roll(prop.id, date(2024, 6, 1), date(2024, 6, 1))[0]
    assert report_jun1['monthly_rent'] == 1500