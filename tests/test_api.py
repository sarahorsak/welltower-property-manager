# tests/test_api.py (Comprehensive Testing)
import json
from datetime import date
import pytest
from src.models import Property, Unit, Resident, Occupancy, Rent, UnitStatus
from src import db

# Use the client and db_session fixtures defined in conftest.py

def test_initial_setup(client, db_session):
    """Test basic creation of all core entities."""
    # Property
    p_res = client.post('/properties', json={"name": "Test Garden"})
    assert p_res.status_code == 201
    prop_id = p_res.json['id']
    
    # Unit
    u_res = client.post('/units', json={"property_id": prop_id, "unit_number": "101"})
    assert u_res.status_code == 201
    unit_id = u_res.json['id']
    
    # Resident
    r_res = client.post('/residents', json={"first_name": "Alice", "last_name": "Smith"})
    assert r_res.status_code == 201
    resident_id = r_res.json['id']
    
    assert db_session.get(Property, prop_id) is not None
    assert db_session.get(Unit, unit_id) is not None
    assert db_session.get(Resident, resident_id) is not None

# --- Testing Core Rent Roll Logic (Time-Varying Data) ---

def test_rent_roll_vacant(client, db_session):
    """Test rent roll on a completely vacant unit."""
    prop = Property(name="Vacant Property")
    unit = Unit(property=prop, unit_number="V01")
    db_session.add_all([prop, unit]); db_session.commit()

    response = client.get(f'/reports/rent-roll?property_id={prop.id}&start_date=2024-01-01&end_date=2024-01-03')
    assert response.status_code == 200
    data = response.json
    
    assert len(data) == 3 # 3 days * 1 unit
    assert data[1]['unit_number'] == "V01"
    assert data[1]['resident_id'] is None
    assert data[1]['monthly_rent'] == 0
    assert data[1]['unit_status'] == 'active'

def test_rent_roll_occupied_and_rent_change(client, db_session):
    """Test rent change over time is reflected correctly in the rent roll."""
    prop = Property(name="Rent Change Property")
    unit = Unit(property=prop, unit_number="R1")
    res = Resident(first_name="Bob", last_name="Test")
    db_session.add_all([prop, unit, res]); db_session.commit()

    # Move In: $1000 on Jan 1
    client.post('/occupancy/move-in', json={
        "resident_id": res.id, "unit_id": unit.id, "move_in_date": "2024-01-01", "initial_rent": 1000
    })
    
    # Rent Change: $1200 on June 1
    occ = Occupancy.query.filter_by(resident_id=res.id).first()
    client.post(f'/occupancy/{occ.id}/rent-change', json={
        "new_rent": 1200, "effective_date": "2024-06-01"
    })
    
    # Fetch rent roll across the change date
    response = client.get(f'/reports/rent-roll?property_id={prop.id}&start_date=2024-05-31&end_date=2024-06-01')
    data = response.json
    
    # May 31: Should be $1000
    assert data[0]['date'] == "2024-05-31"
    assert data[0]['monthly_rent'] == 1000
    
    # June 1: Should be $1200
    assert data[1]['date'] == "2024-06-01"
    assert data[1]['monthly_rent'] == 1200

# --- Testing Data Validations ---

def test_move_in_validation_double_booking(client, db_session):
    """Test validation: Cannot double-book a unit."""
    prop = Property(name="Validation Prop")
    unit = Unit(property=prop, unit_number="V1")
    res1 = Resident(first_name="A", last_name="A")
    res2 = Resident(first_name="B", last_name="B")
    db_session.add_all([prop, unit, res1, res2]); db_session.commit()
    
    # 1. First move in (Jan 1 - Feb 1)
    client.post('/occupancy/move-in', json={
        "resident_id": res1.id, "unit_id": unit.id, "move_in_date": "2024-01-01", "initial_rent": 1000
    })
    occ = Occupancy.query.filter_by(resident_id=res1.id).first()
    client.put(f'/occupancy/{occ.id}/move-out', json={"move_out_date": "2024-02-01"})
    
    # 2. Attempt a move in that OVERLAPS (Jan 15)
    response = client.post('/occupancy/move-in', json={
        "resident_id": res2.id, "unit_id": unit.id, "move_in_date": "2024-01-15", "initial_rent": 1000
    })
    
    assert response.status_code == 400
    assert "already occupied" in response.json['error']

# --- Testing Unit Status (Stretch Goal) ---

def test_unit_status_inactive_prevents_rent_and_occupancy(client, db_session):
    """Test that an inactive unit prevents rent roll entry and move-in."""
    prop = Property(name="Status Prop")
    unit = Unit(property=prop, unit_number="S1")
    res = Resident(first_name="C", last_name="C")
    db_session.add_all([prop, unit, res]); db_session.commit()
    
    # Set unit to INACTIVE from Jan 1
    client.post(f'/units/{unit.id}/status', json={"status": "inactive", "start_date": "2024-01-01"})
    
    # 1. Attempt to move resident in on Jan 1 (should fail)
    response = client.post('/occupancy/move-in', json={
        "resident_id": res.id, "unit_id": unit.id, "move_in_date": "2024-01-01", "initial_rent": 1000
    })
    assert response.status_code == 400
    assert "is inactive" in response.json['error']
    
    # 2. Check rent roll: should show status inactive and 0 rent
    response = client.get(f'/reports/rent-roll?property_id={prop.id}&start_date=2024-01-01&end_date=2024-01-01')
    assert response.status_code == 200
    assert response.json[0]['unit_status'] == 'inactive'
    assert response.json[0]['monthly_rent'] == 0
    
    # 3. Set unit back to ACTIVE from Jan 2 (should succeed)
    client.post(f'/units/{unit.id}/status', json={"status": "active", "start_date": "2024-01-02"})
    
    # 4. Check rent roll for Jan 2: should be vacant/active
    response = client.get(f'/reports/rent-roll?property_id={prop.id}&start_date=2024-01-02&end_date=2024-01-02')
    assert response.json[0]['unit_status'] == 'active'
    assert response.json[0]['resident_id'] is None

# --- Testing KPI API (Stretch Goal) ---

def test_kpi_occupancy_rate_calculation(client, db_session):
    """Tests the complex occupancy rate formula provided in the prompt."""
    prop = Property(name="KPI Prop")
    # Create 50 Units
    units = [Unit(property=prop, unit_number=f"U{i}") for i in range(1, 51)]
    res = [Resident(first_name=f"R{i}", last_name="L") for i in range(1, 42)]
    db_session.add_all([prop] + units + res); db_session.commit()

    # Scenario: 30-day month (e.g., Nov 2024)
    start_date = "2024-11-01"
    end_date = "2024-11-30" # 30 days total
    
    # 1. 39 units occupied for 30 days (1-39)
    for i in range(0, 39):
        client.post('/occupancy/move-in', json={
            "resident_id": res[i].id, "unit_id": units[i].id, 
            "move_in_date": start_date, "initial_rent": 100
        })

    # 2. 2 units occupied for 15 days (40-41)
    unit_40_id = units[39].id
    unit_41_id = units[40].id
    
    # Unit 40: Moves in Nov 16 (15 days occupied: 16th to 30th)
    client.post('/occupancy/move-in', json={
        "resident_id": res[39].id, "unit_id": unit_40_id, 
        "move_in_date": "2024-11-16", "initial_rent": 100
    })
    # Unit 41: Moves in Nov 16 (15 days occupied: 16th to 30th)
    client.post('/occupancy/move-in', json={
        "resident_id": res[40].id, "unit_id": unit_41_id, 
        "move_in_date": "2024-11-16", "initial_rent": 100
    })

    # Expected Occupancy Rate = ((39 * 30) + (2 * 15)) / (50 * 30) = 1200 / 1500 = 0.8
    response = client.get(f'/reports/kpi?property_id={prop.id}&start_date={start_date}&end_date={end_date}')
    assert response.status_code == 200
    data = response.json['2024-11']
    
    assert data['total_units_days'] == 1500 # 50 units * 30 days
    assert data['occupied_days'] == 1200 # (39*30) + (2*15)
    # Asserting near 0.8 to account for floating point
    assert abs(data['occupancy_rate'] - 0.8) < 0.0001 
    
    # Assert movement counts (all happened on Nov 1st/16th, but should be tallied once per move-in)
    assert data['move_ins'] == 41 # 39 on day 1 + 2 on day 16
    assert data['move_outs'] == 0 # No move outs occurred