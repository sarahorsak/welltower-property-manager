# tests/test_logic.py
import pytest
from datetime import date
from src.models import Property, Unit, Resident, Occupancy, Rent, UnitStatus
from src.services.rent_roll import generate_rent_roll
from src.services.kpis import move_in_out_counts, occupancy_rate_for_month

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
    # There should be 4 records, unless a rent change is effective on one of those days (then more)
    # For this test, only one rent, so 4 records
    assert len(report) == 4
    # Dec 31: Vacant
    assert report[0]['date'] == "2023-12-31"
    assert report[0]['monthly_rent'] == 0
    assert report[0]['resident_id'] is None
    # Jan 1: Occupied, $1000
    jan1 = [r for r in report if r['date'] == "2024-01-01" and r['resident_id'] == res.id]
    assert jan1 and jan1[0]['monthly_rent'] == 1000
    # Jan 3: Still Occupied, $1000
    jan3 = [r for r in report if r['date'] == "2024-01-03" and r['resident_id'] == res.id]
    assert jan3 and jan3[0]['monthly_rent'] == 1000

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
    jan1 = [r for r in report if r['date'] == "2024-01-01" and r['resident_id'] == res.id]
    assert jan1 and jan1[0]['monthly_rent'] == 2000
    # Jan 2: Vacant (move-out date is first vacant day)
    jan2 = [r for r in report if r['date'] == "2024-01-02" and r['resident_id'] is None]
    assert jan2 and jan2[0]['monthly_rent'] == 0
    # Jan 3: Vacant
    jan3 = [r for r in report if r['date'] == "2024-01-03" and r['resident_id'] is None]
    assert jan3 and jan3[0]['monthly_rent'] == 0

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
    jan14 = [r for r in report if r['date'] == "2024-01-14" and r['resident_id'] == res.id]
    assert jan14 and jan14[0]['monthly_rent'] == 1000
    # Jan 15: On effective date, should have one records: one for the new rent (change)
    jan15 = [r for r in report if r['date'] == "2024-01-15" and r['resident_id'] == res.id]
    assert len(jan15) == 1
    assert any(r['monthly_rent'] == 1500 for r in jan15)
    # Jan 16: After change, rent is $1500
    jan16 = [r for r in report if r['date'] == "2024-01-16" and r['resident_id'] == res.id]
    assert jan16 and jan16[0]['monthly_rent'] == 1500

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
    jan1 = [r for r in report if r['date'] == "2024-01-01" and r['unit_status'] == 'active']
    assert jan1 and jan1[0]['monthly_rent'] == 1000
    # Jan 2: Inactive, $0 rent, No resident info
    jan2 = [r for r in report if r['date'] == "2024-01-02" and r['unit_status'] == 'inactive']
    assert jan2 and jan2[0]['monthly_rent'] == 0 and jan2[0]['resident_id'] is None

def test_kpi_split_functions(db_session):
    """Test the split KPI service functions: move_in_out_counts and occupancy_rate_for_month."""
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

    # Test occupancy_rate_for_month (June 2024)
    occ = occupancy_rate_for_month(prop.id, 2024, 6)
    assert occ['total_units_days'] == 60
    assert occ['occupied_days'] == 29
    assert abs(occ['occupancy_rate'] - 0.4833) < 0.0001

    # Test move_in_out_counts (June 1 - June 30)
    moves = move_in_out_counts(prop.id, date(2024, 6, 1), date(2024, 6, 30))
    assert moves['move_ins'] == 1
    assert moves['move_outs'] == 1


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

    moves = move_in_out_counts(prop.id, date(2024, 4, 1), date(2024, 4, 30))
    occ = occupancy_rate_for_month(prop.id, 2024, 4)

    # Expect one move-in (on Apr 1) and one move-out (on Apr 30)
    assert moves['move_ins'] == 1
    assert moves['move_outs'] == 1
    # Optionally check occupancy rate keys exist
    assert 'occupancy_rate' in occ


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
