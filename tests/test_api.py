# tests/test_api.py (Comprehensive Testing)
import json
from datetime import date
import pytest
from src.models import Property, Unit, Resident, Occupancy, Rent, UnitStatus

# Small helper to reduce repetition when creating property/unit/resident via API
def _create_prop_unit_res(client, prop_name="P", unit_number="1", first="F", last="L"):
    p = client.post('/properties', json={"name": prop_name}).json
    u = client.post('/units', json={"property_id": p['id'], "unit_number": unit_number}).json
    r = client.post('/residents', json={"first_name": first, "last_name": last}).json
    return p, u, r

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
    unit = Unit(property=prop, unit_number="1")
    db_session.add_all([prop, unit]); db_session.commit()

    response = client.get(f'/reports/rent-roll?property_id={prop.id}&start_date=2024-01-01&end_date=2024-01-03')
    assert response.status_code == 200
    data = response.json
    
    assert len(data) == 3 # 3 days * 1 unit
    assert data[1]['unit_number'] == "P1-U1"
    assert data[1]['resident_id'] is None
    assert data[1]['monthly_rent'] == 0
    assert data[1]['unit_status'] == 'active'

# --- Testing Data Validations ---

@pytest.mark.parametrize("first_move_in,second_move_in,expect_status", [
    ("2024-01-01", "2024-01-01", 400),  # same-day collision
    ("2024-01-01", "2024-01-15", 400),  # overlapping while first still active (no move-out)
])
def test_move_in_overlap_variants(client, db_session, first_move_in, second_move_in, expect_status):
    """Parametrized test for overlapping move-in validations (reduces duplicate tests)."""
    # Use helper to create resources
    p, u, r1 = _create_prop_unit_res(client, prop_name="OverlapAPIProp", unit_number="1", first="sarah", last="smith")
    # create second resident via API
    r2 = client.post('/residents', json={"first_name": "Jack", "last_name": "Smith"}).json

    # First move-in
    ok = client.post('/occupancy/move-in', json={
        "resident_id": r1['id'], "unit_id": u['id'], "move_in_date": first_move_in, "initial_rent": 600
    })
    assert ok.status_code == 201

    # Attempt second move-in
    resp = client.post('/occupancy/move-in', json={
        "resident_id": r2['id'], "unit_id": u['id'], "move_in_date": second_move_in, "initial_rent": 600
    })
    assert resp.status_code == expect_status
    if expect_status == 400:
        assert "already occupied" in resp.json.get('error', '').lower()

# --- Testing Unit Status (Stretch Goal) ---

def test_unit_status_inactive_prevents_rent_and_occupancy(client, db_session):
    """Test that an inactive unit prevents rent roll entry and move-in."""
    prop = Property(name="Status Prop")
    unit = Unit(property=prop, unit_number="2")
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

def test_kpi_occupancy_and_move_counts_endpoints(client, db_session):
    """Test the split KPI endpoints: /reports/kpi-move and /reports/kpi-occupancy."""
    prop = Property(name="KPI Prop")
    units = [Unit(property=prop, unit_number=str(i)) for i in range(1, 51)]
    res = [Resident(first_name=f"R{i}", last_name="L") for i in range(1, 42)]
    db_session.add_all([prop] + units + res); db_session.commit()

    start_date = "2024-11-01"
    end_date = "2024-11-30"

    # 39 units occupied for 30 days
    for i in range(0, 39):
        client.post('/occupancy/move-in', json={
            "resident_id": res[i].id, "unit_id": units[i].id,
            "move_in_date": start_date, "initial_rent": 100
        })

    # 2 units occupied for 15 days (move in Nov 16)
    for i in range(39, 41):
        client.post('/occupancy/move-in', json={
            "resident_id": res[i].id, "unit_id": units[i].id,
            "move_in_date": "2024-11-16", "initial_rent": 100
        })

    # Test /reports/kpi-occupancy
    occ_resp = client.get(f'/reports/kpi-occupancy?property_id={prop.id}&year=2024&month=11')
    assert occ_resp.status_code == 200
    occ_data = occ_resp.json
    assert occ_data['total_units_days'] == 1500
    assert occ_data['occupied_days'] == 1200
    assert abs(occ_data['occupancy_rate'] - 0.8) < 0.0001

    # Test /reports/kpi-move
    move_resp = client.get(f'/reports/kpi-move?property_id={prop.id}&start_date={start_date}&end_date={end_date}')
    assert move_resp.status_code == 200
    move_data = move_resp.json
    assert move_data['move_ins'] == 41
    assert move_data['move_outs'] == 0

def test_rent_change_endpoint_and_effect_on_rent_roll(client, db_session):
    # Create resources via API
    p = client.post('/properties', json={"name": "RentChangeAPIProp"}).json
    u = client.post('/units', json={"property_id": p['id'], "unit_number": "1"}).json
    r = client.post('/residents', json={"first_name": "API", "last_name": "User"}).json

    # Move in via API
    move_in_res = client.post('/occupancy/move-in', json={
        "resident_id": r['id'],
        "unit_id": u['id'],
        "move_in_date": "2024-01-01",
        "initial_rent": 1000
    })
    assert move_in_res.status_code == 201
    occ_id = move_in_res.json['id']

    # Add a rent change effective 2024-06-01
    rc = client.post(f'/occupancy/{occ_id}/rent-change', json={
        "new_rent": 1200, "effective_date": "2024-06-01"
    })
    assert rc.status_code == 201

    # Verify rent roll shows old rent on 2024-05-31 and new rent on 2024-06-01
    res = client.get(f"/reports/rent-roll?property_id={p['id']}&start_date=2024-05-31&end_date=2024-06-01")
    assert res.status_code == 200
    data = res.json
    assert data[0]['monthly_rent'] == 1000
    assert data[1]['monthly_rent'] == 1200


def test_move_out_before_move_in_returns_400_via_api(client, db_session):
    # Create property/unit/resident
    p = client.post('/properties', json={"name": "MoveOutValidationProp"}).json
    u = client.post('/units', json={"property_id": p['id'], "unit_number": "3"}).json
    r = client.post('/residents', json={"first_name": "M", "last_name": "O"}).json

    # Move in normally
    mi = client.post('/occupancy/move-in', json={
        "resident_id": r['id'],
        "unit_id": u['id'],
        "move_in_date": "2024-04-15",
        "initial_rent": 500
    })
    occ_id = mi.json['id']

    # Attempt move-out with a date before move-in
    bad = client.put(f'/occupancy/{occ_id}/move-out', json={"move_out_date": "2024-04-01"})
    assert bad.status_code == 400
    assert "move-out date" in bad.json['error'].lower()


def test_create_unit_with_invalid_property_returns_404(client):
    res = client.post('/units', json={"property_id": 999999, "unit_number": "4"})
    assert res.status_code == 404
    assert "Property not found" in res.json.get('error', '')


def test_rent_change_invalid_date_format_returns_400(client, db_session):
    # create via API
    p = client.post('/properties', json={"name": "BadDateRentProp"}).json
    u = client.post('/units', json={"property_id": p['id'], "unit_number": "1"}).json
    r = client.post('/residents', json={"first_name": "D", "last_name": "F"}).json

    mi = client.post('/occupancy/move-in', json={
        "resident_id": r['id'], "unit_id": u['id'], "move_in_date": "2024-01-01", "initial_rent": 400
    })
    occ_id = mi.json['id']

    bad = client.post(f'/occupancy/{occ_id}/rent-change', json={"new_rent": 500, "effective_date": "06-01-2024"})
    assert bad.status_code == 400
    assert "Invalid date format" in bad.json.get('error', '')


def test_unit_status_duplicate_date_returns_400(client, db_session):
    p = client.post('/properties', json={"name": "StatusDupProp"}).json
    u = client.post('/units', json={"property_id": p['id'], "unit_number": "12"}).json

    # First status change succeeds
    ok = client.post(f'/units/{u["id"]}/status', json={"status": "inactive", "start_date": "2024-07-01"})
    assert ok.status_code == 201

    # Second on same date should fail
    dup = client.post(f'/units/{u["id"]}/status', json={"status": "active", "start_date": "2024-07-01"})
    assert dup.status_code == 400
    assert "already exists" in dup.json.get('error', '')


def test_rent_roll_includes_vacant_units_and_counts_correctly(client, db_session):
    # Create property + two units
    p = client.post('/properties', json={"name": "VacancyAPIProp"}).json
    u1 = client.post('/units', json={"property_id": p['id'], "unit_number": "1"}).json
    u2 = client.post('/units', json={"property_id": p['id'], "unit_number": "2"}).json

    # No occupancies -> rent-roll should include both units for each day
    res = client.get(f"/reports/rent-roll?property_id={p['id']}&start_date=2024-08-01&end_date=2024-08-02")
    assert res.status_code == 200
    entries = res.json
    # 2 days * 2 units = 4 entries
    assert len(entries) == 4
    # Ensure per-day ordering exists (each date appears twice)
    dates = [e['date'] for e in entries]
    assert dates.count("2024-08-01") == 2
    assert dates.count("2024-08-02") == 2


def test_kpi_split_api_missing_or_bad_params_return_400(client):
    # /reports/kpi-occupancy missing params
    r1 = client.get('/reports/kpi-occupancy')
    assert r1.status_code == 400
    # Bad year/month
    r2 = client.get('/reports/kpi-occupancy?property_id=1&year=2024&month=13')
    assert r2.status_code == 400

    # /reports/kpi-move missing params
    r3 = client.get('/reports/kpi-move')
    assert r3.status_code == 400
    # Bad date format
    r4 = client.get('/reports/kpi-move?property_id=1&start_date=2024/01/01&end_date=2024-01-31')
    assert r4.status_code == 400
    assert "Invalid date format" in r4.json.get('error', '')


def test_get_endpoints_list_and_detail(client, db_session):
    """Test the newly-added GET endpoints for list and detail views."""
    # Create a property/unit/resident via API
    p = client.post('/properties', json={"name": "GetTestProp"}).json
    u = client.post('/units', json={"property_id": p['id'], "unit_number": "1"}).json
    r = client.post('/residents', json={"first_name": "G", "last_name": "User"}).json

    # GET all properties
    props = client.get('/properties')
    assert props.status_code == 200
    assert any(item['id'] == p['id'] for item in props.json)

    # GET property detail
    prop_detail = client.get(f"/properties/{p['id']}")
    assert prop_detail.status_code == 200
    assert prop_detail.json['id'] == p['id']

    # GET property's units
    prop_units = client.get(f"/properties/{p['id']}/units")
    assert prop_units.status_code == 200
    assert any(u_item['id'] == u['id'] for u_item in prop_units.json)

    # GET units list and unit detail
    units = client.get('/units')
    assert units.status_code == 200
    unit_detail = client.get(f"/units/{u['id']}")
    assert unit_detail.status_code == 200
    assert unit_detail.json['id'] == u['id']

    # GET residents list and resident detail
    residents = client.get('/residents')
    assert residents.status_code == 200
    resident_detail = client.get(f"/residents/{r['id']}")
    assert resident_detail.status_code == 200
    assert resident_detail.json['id'] == r['id']


def test_occupancy_rents_history_endpoint(client, db_session):
    """Create an occupancy and rent changes, then verify the rents history GET endpoint."""
    p = client.post('/properties', json={"name": "RentHistoryProp"}).json
    u = client.post('/units', json={"property_id": p['id'], "unit_number": "120"}).json
    r = client.post('/residents', json={"first_name": "RH", "last_name": "Res"}).json
    mi = client.post('/occupancy/move-in', json={
        "resident_id": r['id'], "unit_id": u['id'], "move_in_date": "2024-01-01", "initial_rent": 900
    })
    assert mi.status_code == 201
    occ_id = mi.json.get('id')
    if occ_id is None:
        print("Occupancy creation response:", mi.json)
    assert occ_id is not None, "Occupancy creation did not return an id"

    # Add two rent changes
    rc1 = client.post(f"/occupancy/{occ_id}/rent-change", json={"new_rent": 1000, "effective_date": "2024-02-01"})
    rc2 = client.post(f"/occupancy/{occ_id}/rent-change", json={"new_rent": 1100, "effective_date": "2024-03-01"})
    assert rc1.status_code == 201 and rc2.status_code == 201

    rents = client.get(f"/occupancy/{occ_id}/rents")
    assert rents.status_code == 200
    # Expect at least 3 rent records (initial + two changes)
    assert len(rents.json) >= 3
    amounts = [r_entry['amount'] for r_entry in rents.json]
    assert 1000 in amounts and 1100 in amounts


@pytest.mark.parametrize("endpoint, payload, error_field", [
    ('/properties', {"name": ""}, 'Property name'),
    ('/properties', {"name": "   "}, 'Property name'),
    ('/units', {"property_id": 1, "unit_number": ""}, 'unit_number'),
    ('/units', {"property_id": 1, "unit_number": "   "}, 'unit_number'),
    ('/residents', {"first_name": "", "last_name": "Smith"}, 'first_name'),
    ('/residents', {"first_name": "John", "last_name": ""}, 'last_name'),
    ('/residents', {"first_name": "   ", "last_name": "Smith"}, 'first_name'),
    ('/residents', {"first_name": "John", "last_name": "   "}, 'last_name'),
])
def test_empty_and_whitespace_input_returns_400(client, db_session, endpoint, payload, error_field):
    # For /units, ensure property exists first
    if endpoint == '/units':
        client.post('/properties', json={"name": "EmptyInputProp"})
        payload["property_id"] = 1
    resp = client.post(endpoint, json=payload)
    assert resp.status_code == 400
    assert error_field.lower() in resp.json.get('error', '').lower()