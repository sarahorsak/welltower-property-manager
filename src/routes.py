# src/routes.py
from flask import request, jsonify, Blueprint
from sqlalchemy import or_
from . import db
from .models import Property, Unit, Resident, Occupancy, Rent, UnitStatus
from .logic import generate_rent_roll, calculate_kpis
from datetime import date

# Use a Blueprint to organize routes
main = Blueprint('main', __name__)

@main.route('/')
def index():
    return "Hello, Welltower!"

# --- Property Routes ---

@main.route('/properties', methods=['POST'])
def create_property():
    data = request.json
    if not data or not data.get('name'):
        return jsonify({'error': 'Property name is required'}), 400
    
    prop = Property(name=data['name'])
    db.session.add(prop)
    db.session.commit()
    return jsonify(prop.to_dict()), 201

@main.route('/properties', methods=['GET'])
def get_properties():
    props = Property.query.all()
    return jsonify([p.to_dict() for p in props]), 200

# --- Unit Routes ---

@main.route('/units', methods=['POST'])
def create_unit():
    data = request.json
    if not data or not data.get('property_id') or not data.get('unit_number'):
        return jsonify({'error': 'property_id and unit_number are required'}), 400
    
    prop = Property.query.get(data['property_id'])
    if not prop:
        return jsonify({'error': 'Property not found'}), 404
        
    unit = Unit(property_id=data['property_id'], unit_number=data['unit_number'])
    db.session.add(unit)
    db.session.commit()
    return jsonify(unit.to_dict()), 201

@main.route('/units/<int:id>/status', methods=['POST'])
def set_unit_status(id):
    data = request.json
    required_fields = ['status', 'start_date']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing status or start_date'}), 400
        
    unit = Unit.query.get(id)
    if not unit:
        return jsonify({'error': 'Unit not found'}), 404
        
    try:
        start_dt = date.fromisoformat(data['start_date'])
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    if data['status'] not in ['active', 'inactive']:
        return jsonify({'error': 'Status must be "active" or "inactive"'}), 400

    # Validation: Prevent creating a status event that starts on the same day as an existing one
    if UnitStatus.query.filter_by(unit_id=id, start_date=start_dt).first():
        return jsonify({'error': f'A status change already exists for unit {id} on {start_dt}'}), 400
    
    status_rec = UnitStatus(
        unit_id=id,
        status=data['status'],
        start_date=start_dt
    )
    db.session.add(status_rec)
    db.session.commit()
    return jsonify({'message': 'Unit status change logged'}), 201

# --- Resident Routes ---

@main.route('/residents', methods=['POST'])
def create_resident():
    data = request.json
    if not data or not data.get('first_name') or not data.get('last_name'):
        return jsonify({'error': 'first_name and last_name are required'}), 400
        
    res = Resident(first_name=data['first_name'], last_name=data['last_name'])
    db.session.add(res)
    db.session.commit()
    return jsonify(res.to_dict()), 201


# --- Core Business Logic Routes ---

@main.route('/occupancy/move-in', methods=['POST'])
def move_in():
    data = request.json
    # Basic validation
    required_fields = ['resident_id', 'unit_id', 'move_in_date', 'initial_rent']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing fields'}), 400
        
    move_in_dt = date.fromisoformat(data['move_in_date'])
    unit = Unit.query.get(data['unit_id'])
    
    # Validation 1: Unit must exist
    if not unit:
        return jsonify({'error': 'Unit not found'}), 404
    
    # Validation 2: Unit must be active on move-in date
    if unit.get_status_on_date(move_in_dt) == 'inactive':
        return jsonify({'error': f'Unit {unit.unit_number} is inactive on {move_in_dt.isoformat()}'}), 400
    
    # Validation 3: Unit cannot be double-booked (overlap with existing occupancy)
    # Check for existing occupancy where [move_in_date] is between [existing_in] and [existing_out]
    # OR where [existing_in] is between [move_in_date] and [move_in_date] (i.e., exact overlap)
    existing_occupancy = Occupancy.query.filter(
        Occupancy.unit_id == data['unit_id'],
        Occupancy.move_in_date <= move_in_dt,
        or_(Occupancy.move_out_date == None, Occupancy.move_out_date > move_in_dt)
    ).first()

    if existing_occupancy:
        return jsonify({'error': f'Unit {unit.unit_number} is already occupied on {move_in_dt.isoformat()}'}), 400
    
    # Create the Occupancy record and initial Rent
    occ = Occupancy(
        resident_id=data['resident_id'],
        unit_id=data['unit_id'],
        move_in_date=move_in_dt
    )
    db.session.add(occ)
    
    rent = Rent(
        occupancy=occ,
        amount=data['initial_rent'],
        effective_date=move_in_dt
    )
    db.session.add(rent)
    db.session.commit()
    
    return jsonify({'message': 'Move-in successful', 'occupancy_id': occ.id}), 201
    

@main.route('/occupancy/<int:id>/move-out', methods=['PUT'])
def move_out(id):
    data = request.json
    if not data or not data.get('move_out_date'):
        return jsonify({'error': 'move_out_date is required'}), 400
        
    occ = Occupancy.query.get(id)
    if not occ:
        return jsonify({'error': 'Occupancy record not found'}), 404
    
    move_out_dt = date.fromisoformat(data['move_out_date'])
    
    # Validation: move-out date must be on or after move-in date
    if move_out_dt < occ.move_in_date:
        return jsonify({'error': 'Move-out date must be on or after move-in date.'}), 400
    
    occ.move_out_date = move_out_dt
    db.session.commit()
    return jsonify({'message': 'Move-out successful'}), 200


@main.route('/occupancy/<int:id>/rent-change', methods=['POST'])
def rent_change(id):
    """
    Log a new rent amount for an occupancy with an effective date.
    Expected JSON: { "new_rent": <int>, "effective_date": "YYYY-MM-DD" }
    """
    data = request.json
    if not data or 'new_rent' not in data or 'effective_date' not in data:
        return jsonify({'error': 'new_rent and effective_date are required'}), 400

    occ = Occupancy.query.get(id)
    if not occ:
        return jsonify({'error': 'Occupancy not found'}), 404

    try:
        eff_date = date.fromisoformat(data['effective_date'])
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    # Create new Rent record
    rent = Rent(
        occupancy_id=occ.id,
        amount=data['new_rent'],
        effective_date=eff_date
    )
    db.session.add(rent)
    db.session.commit()

    return jsonify({'message': 'Rent change logged', 'rent_id': rent.id}), 201


# --- Reporting Routes ---

@main.route('/reports/rent-roll', methods=['GET'])
def get_rent_roll():
    property_id = request.args.get('property_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not all([property_id, start_date, end_date]):
        return jsonify({'error': 'property_id, start_date, and end_date are required'}), 400
        
    try:
        start_dt = date.fromisoformat(start_date)
        end_dt = date.fromisoformat(end_date)
        prop_id = int(property_id)
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid format for dates (YYYY-MM-DD) or property_id (integer)'}), 400

    # Validation: end_date must be on or after start_date
    if end_dt < start_dt:
        return jsonify({'error': 'End date must be on or after start date.'}), 400
        
    rent_roll_data = generate_rent_roll(prop_id, start_dt, end_dt)
    
    return jsonify(rent_roll_data), 200

# --- KPI API (Stretch Goal) ---

@main.route('/reports/kpi', methods=['GET'])
def get_kpis():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    property_id = request.args.get('property_id') # Added property scope for realism
    
    if not all([start_date, end_date, property_id]):
        return jsonify({'error': 'start_date, end_date, and property_id are required'}), 400
        
    try:
        start_dt = date.fromisoformat(start_date)
        end_dt = date.fromisoformat(end_date)
        prop_id = int(property_id)
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    kpi_data = calculate_kpis(prop_id, start_dt, end_dt)
    
    return jsonify(kpi_data), 200