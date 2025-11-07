# src/routes.py
from flask import request, jsonify, Blueprint, Response, render_template
from sqlalchemy import or_
from . import db
from .models import Property, Unit, Resident, Occupancy, Rent, UnitStatus
from .services.rent_roll import generate_rent_roll
from .services.kpis import calculate_kpis
from datetime import date
import csv
import io

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


@main.route('/properties/<int:id>', methods=['GET'])
def get_property(id):
    prop = Property.query.get(id)
    if not prop:
        return jsonify({'error': 'Property not found'}), 404
    return jsonify(prop.to_dict()), 200


@main.route('/properties/<int:id>/units', methods=['GET'])
def get_property_units(id):
    prop = Property.query.get(id)
    if not prop:
        return jsonify({'error': 'Property not found'}), 404

    units = Unit.query.filter_by(property_id=id).all()
    return jsonify([u.to_dict() for u in units]), 200

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


@main.route('/units', methods=['GET'])
def list_units():
    # optional filter by property_id
    property_id = request.args.get('property_id')
    if property_id:
        try:
            pid = int(property_id)
        except ValueError:
            return jsonify({'error': 'property_id must be an integer'}), 400
        units = Unit.query.filter_by(property_id=pid).all()
    else:
        units = Unit.query.all()
    return jsonify([u.to_dict() for u in units]), 200


@main.route('/units/<int:id>', methods=['GET'])
def get_unit(id):
    unit = Unit.query.get(id)
    if not unit:
        return jsonify({'error': 'Unit not found'}), 404
    # include current status if model supports it
    data = unit.to_dict()
    try:
        # unit.get_status_on_date exists in models; show current status for today
        data['current_status'] = unit.get_status_on_date(date.today())
    except Exception:
        pass
    return jsonify(data), 200

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


@main.route('/units/<int:id>/status', methods=['GET'])
def get_unit_status(id):
    """
    Get the unit's current status and history or the status on a specific date.
    Query param: date=YYYY-MM-DD (optional). If provided, returns the status on that date.
    Otherwise returns current_status and full status history for the unit.
    """
    unit = Unit.query.get(id)
    if not unit:
        return jsonify({'error': 'Unit not found'}), 404

    date_str = request.args.get('date')
    if date_str:
        try:
            qdate = date.fromisoformat(date_str)
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        status_on_date = unit.get_status_on_date(qdate)
        return jsonify({'unit_id': id, 'date': qdate.isoformat(), 'status': status_on_date}), 200

    # No date provided: return current status and history
    current_status = unit.get_status_on_date(date.today())
    history = []
    for s in unit.status_history.order_by(UnitStatus.start_date).all():
        history.append({'id': s.id, 'status': s.status, 'start_date': s.start_date.isoformat()})

    return jsonify({'unit_id': id, 'current_status': current_status, 'history': history}), 200

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


@main.route('/residents', methods=['GET'])
def list_residents():
    # optional filter by property_id
    property_id = request.args.get('property_id')
    if property_id:
        try:
            pid = int(property_id)
        except ValueError:
            return jsonify({'error': 'property_id must be an integer'}), 400
        # join via Occupancy->Unit to find residents in a property
        residents = Resident.query.join(Occupancy, isouter=True).join(Unit, isouter=True).filter(Unit.property_id == pid).all()
    else:
        residents = Resident.query.all()
    return jsonify([r.to_dict() for r in residents]), 200


@main.route('/residents/<int:id>', methods=['GET'])
def get_resident(id):
    res = Resident.query.get(id)
    if not res:
        return jsonify({'error': 'Resident not found'}), 404
    # include current occupancy if present
    data = res.to_dict()
    try:
        occ = Occupancy.query.filter_by(resident_id=res.id, move_out_date=None).first()
        if occ:
            data['current_occupancy'] = occ.to_dict()
    except Exception:
        pass
    return jsonify(data), 200


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


@main.route('/occupancy/<int:id>/rents', methods=['GET'])
def occupancy_rents(id):
    occ = Occupancy.query.get(id)
    if not occ:
        return jsonify({'error': 'Occupancy not found'}), 404
    rents = Rent.query.filter_by(occupancy_id=id).order_by(Rent.effective_date).all()
    return jsonify([{'id': r.id, 'amount': r.amount, 'effective_date': r.effective_date.isoformat()} for r in rents]), 200


# --- Occupancy list (support for admin UI) ---
@main.route('/occupancies', methods=['GET'])
def list_occupancies():
    """Return all occupancies with related unit/resident info for admin UI."""
    occs = Occupancy.query.order_by(Occupancy.move_in_date).all()
    out = []
    for o in occs:
        unit = Unit.query.get(o.unit_id)
        resident = Resident.query.get(o.resident_id)
        out.append({
            'id': o.id,
            'unit_id': o.unit_id,
            'unit_number': unit.unit_number if unit else None,
            'resident_id': o.resident_id,
            'resident_name': f"{resident.first_name} {resident.last_name}" if resident else None,
            'move_in_date': o.move_in_date.isoformat() if o.move_in_date else None,
            'move_out_date': o.move_out_date.isoformat() if o.move_out_date else None,
        })
    return jsonify(out), 200


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
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD for dates and integer for property_id'}), 400

    # Validation: end_date must be on or after start_date
    if end_dt < start_dt:
        return jsonify({'error': 'End date must be on or after start date.'}), 400
        
    rent_roll_data = generate_rent_roll(prop_id, start_dt, end_dt)
    # Support CSV download when format=csv is provided
    fmt = request.args.get('format')
    if fmt == 'csv':
        # Create CSV in-memory
        output = io.StringIO()
        writer = None
        for row in rent_roll_data:
            if writer is None:
                # header from keys
                writer = csv.DictWriter(output, fieldnames=list(row.keys()))
                writer.writeheader()
            writer.writerow(row)
        csv_data = output.getvalue()
        output.close()
        headers = {
            'Content-Type': 'text/csv',
            'Content-Disposition': f'attachment; filename="rent_roll_{prop_id}_{start_dt.isoformat()}_{end_dt.isoformat()}.csv"'
        }
        return Response(csv_data, headers=headers)

    return jsonify(rent_roll_data), 200

# --- KPI API (Stretch Goal) ---

@main.route('/reports/kpi', methods=['GET'])
def get_kpis():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    property_id = request.args.get('property_id')

    if not all([start_date, end_date, property_id]):
        return jsonify({'error': 'start_date, end_date, and property_id are required'}), 400

    try:
        start_dt = date.fromisoformat(start_date)
        end_dt = date.fromisoformat(end_date)
        prop_id = int(property_id)
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD for dates and integer for property_id'}), 400

    kpis = calculate_kpis(prop_id, start_dt, end_dt)
    return jsonify(kpis), 200


@main.route('/admin', methods=['GET'])
def admin_ui():
    # Admin UI served from templates/admin.html and static/admin.js
    return render_template('admin.html')


# --- Unit-level aggregated rent history (new)
@main.route('/units/<int:unit_id>/rents', methods=['GET'])
def unit_rents(unit_id):
    """
    Return aggregated rent history for a unit by collecting rents from all occupancies
    for that unit. Response shape: list of { occupancy_id, resident_id, resident_name, start_date, end_date, monthly_rent }
    """
    unit = Unit.query.get(unit_id)
    if not unit:
        return jsonify({'error': 'Unit not found'}), 404

    occs = unit.occupancies.order_by(Occupancy.move_in_date).all()
    out = []
    for occ in occs:
        resident = occ.resident
        # For each rent change on the occupancy, include effective_date and amount
        rents = Rent.query.filter_by(occupancy_id=occ.id).order_by(Rent.effective_date).all()
        # If there are no explicit rent records, still include an entry representing the occupancy
        if not rents:
            out.append({
                'occupancy_id': occ.id,
                'resident_id': resident.id if resident else None,
                'resident_name': resident.full_name if resident else None,
                'move_in_date': occ.move_in_date.isoformat() if occ.move_in_date else None,
                'move_out_date': occ.move_out_date.isoformat() if occ.move_out_date else None,
                'monthly_rent': None
            })
        else:
            for r in rents:
                out.append({
                    'occupancy_id': occ.id,
                    'resident_id': resident.id if resident else None,
                    'resident_name': resident.full_name if resident else None,
                    'effective_date': r.effective_date.isoformat(),
                    'monthly_rent': r.amount
                })

    return jsonify(out), 200