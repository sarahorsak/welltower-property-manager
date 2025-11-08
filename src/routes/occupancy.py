
from flask import Blueprint, request, jsonify
from ..models import Occupancy, Unit, Resident, Rent
from .. import db
from sqlalchemy import or_, and_
from datetime import date

occupancy_bp = Blueprint('occupancy', __name__)

@occupancy_bp.route('/occupancy/move-in', methods=['POST'])
def move_in():
    data = request.json
    required_fields = ['resident_id', 'unit_id', 'move_in_date', 'initial_rent']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing fields'}), 400
    # Resident cannot have overlapping occupancies
    occs = Occupancy.query.filter_by(resident_id=data['resident_id']).all()
    move_in_dt = date.fromisoformat(data['move_in_date'])
    move_out_date = data.get('move_out_date')
    for occ in occs:
        occ_end = occ.move_out_date or date.max
        if (occ.move_in_date <= move_in_dt < occ_end) or (move_out_date and occ.move_in_date < date.fromisoformat(move_out_date) <= occ_end):
            return jsonify({'error': 'Resident has overlapping occupancy'}), 400
    # Only validate if both move_in_date and move_out_date are present
    if move_out_date:
        move_out_dt = date.fromisoformat(move_out_date)
        if move_in_dt >= move_out_dt:
            return jsonify({'error': 'Move-in date must be before move-out date'}), 400
    unit = db.session.get(Unit, data['unit_id'])
    if not unit:
        return jsonify({'error': 'Unit not found'}), 404
    if unit.get_status_on_date(move_in_dt) == 'inactive':
        return jsonify({'error': f'Unit {unit.unit_number} is inactive on {move_in_dt.isoformat()}'}), 400
    # No overlapping occupancies for the same unit
    existing_occupancy = Occupancy.query.filter(
        Occupancy.unit_id == data['unit_id'],
        Occupancy.move_in_date <= move_in_dt,
        or_(Occupancy.move_out_date == None, Occupancy.move_out_date > move_in_dt)
    ).first()
    if existing_occupancy:
        return jsonify({'error': f'Unit {unit.unit_number} is already occupied on {move_in_dt.isoformat()}'}), 400
    occ = Occupancy(
        resident_id=data['resident_id'],
        unit_id=data['unit_id'],
        move_in_date=move_in_dt
    )
    db.session.add(occ)
    # Rent must be positive integer
    try:
        rent_amt = int(data['initial_rent'])
    except Exception:
        return jsonify({'error': 'initial_rent must be an integer'}), 400
    if rent_amt <= 0:
        return jsonify({'error': 'initial_rent must be positive'}), 400
    rent = Rent(
        occupancy=occ,
        amount=rent_amt,
        effective_date=move_in_dt
    )
    db.session.add(rent)
    db.session.commit()
    return jsonify(occ.to_dict()), 201

@occupancy_bp.route('/occupancy/<int:id>/move-out', methods=['PUT'])
def move_out(id):
    data = request.json
    if not data or not data.get('move_out_date'):
        return jsonify({'error': 'move_out_date is required'}), 400
    occ = db.session.get(Occupancy, id)
    if not occ:
        return jsonify({'error': 'Occupancy record not found'}), 404
    move_in_date = occ.move_in_date
    move_out_date = data.get('move_out_date')
    if not move_in_date or not move_out_date:
        return jsonify({'error': 'Both move-in and move-out dates must be provided for validation.'}), 400
    move_out_dt = date.fromisoformat(move_out_date)
    if move_out_dt <= move_in_date:
        return jsonify({'error': 'Move-out date must be after move-in date.'}), 400
    occ.move_out_date = move_out_dt
    db.session.commit()
    return jsonify({'message': 'Move-out successful'}), 200

@occupancy_bp.route('/occupancy/<int:id>/rent-change', methods=['POST'])
def rent_change(id):
    data = request.json
    if not data or 'new_rent' not in data or 'effective_date' not in data:
        return jsonify({'error': 'new_rent and effective_date are required'}), 400
    occ = db.session.get(Occupancy, id)
    if not occ:
        return jsonify({'error': 'Occupancy not found'}), 404
    try:
        eff_date = date.fromisoformat(data['effective_date'])
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    # Prevent duplicate rent records for same date and amount
    existing = Rent.query.filter_by(occupancy_id=occ.id, effective_date=eff_date, amount=data['new_rent']).first()
    if existing:
        return jsonify({'error': 'A rent record with this amount and date already exists.'}), 400
    # Rent must be positive integer
    try:
        rent_amt = int(data['new_rent'])
    except Exception:
        return jsonify({'error': 'new_rent must be an integer'}), 400
    if rent_amt <= 0:
        return jsonify({'error': 'new_rent must be positive'}), 400
    # Effective date must be within occupancy period
    if eff_date < occ.move_in_date or (occ.move_out_date and eff_date >= occ.move_out_date):
        return jsonify({'error': 'effective_date must be within occupancy period'}), 400
    rent = Rent(
        occupancy_id=occ.id,
        amount=rent_amt,
        effective_date=eff_date
    )
    db.session.add(rent)
    db.session.commit()
    return jsonify(rent.to_dict()), 201

@occupancy_bp.route('/occupancy/<int:id>/rents', methods=['GET'])
def occupancy_rents(id):
    occ = db.session.get(Occupancy, id)
    if not occ:
        return jsonify({'error': 'Occupancy not found'}), 404
    rents = Rent.query.filter_by(occupancy_id=id).order_by(Rent.effective_date).all()
    return jsonify([{'id': r.id, 'amount': r.amount, 'effective_date': r.effective_date.isoformat()} for r in rents]), 200

@occupancy_bp.route('/occupancies', methods=['GET'])
def list_occupancies():
    occs = Occupancy.query.order_by(Occupancy.move_in_date).all()
    out = []
    for o in occs:
        unit = db.session.get(Unit, o.unit_id)
        resident = db.session.get(Resident, o.resident_id)
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


# PATCH endpoint to amend occupancy (move-in/move-out dates, unit assignment)
@occupancy_bp.route('/occupancy/<int:id>', methods=['PATCH'])
def update_occupancy(id):
    data = request.json
    occ = db.session.get(Occupancy, id)
    if not occ:
        return jsonify({'error': 'Occupancy not found'}), 404
    move_in_date = data.get('move_in_date')
    move_out_date = data.get('move_out_date')
    unit_id = data.get('unit_id')
    # Validate move-in/move-out dates
    if move_in_date:
        try:
            move_in_dt = date.fromisoformat(move_in_date)
        except Exception:
            return jsonify({'error': 'Invalid move_in_date format'}), 400
    else:
        move_in_dt = occ.move_in_date
    if move_out_date:
        try:
            move_out_dt = date.fromisoformat(move_out_date)
        except Exception:
            return jsonify({'error': 'Invalid move_out_date format'}), 400
    else:
        move_out_dt = occ.move_out_date
    if move_in_dt and move_out_dt and move_in_dt >= move_out_dt:
        return jsonify({'error': 'Move-in date must be before move-out date'}), 400
    # Validate unit assignment
    if unit_id:
        unit = db.session.get(Unit, unit_id)
        if not unit:
            return jsonify({'error': 'Unit not found'}), 404
        # Check unit is active for new move-in date
        if unit.get_status_on_date(move_in_dt) == 'inactive':
            return jsonify({'error': f'Unit {unit.unit_number} is inactive on {move_in_dt.isoformat()}'}), 400
        # Check for overlapping occupancies
        overlap = Occupancy.query.filter(
            Occupancy.unit_id == unit_id,
            Occupancy.id != id,
            Occupancy.move_in_date < (move_out_dt or date.max),
            or_(Occupancy.move_out_date == None, Occupancy.move_out_date > move_in_dt)
        ).first()
        if overlap:
            return jsonify({'error': 'Unit is already occupied during the specified period'}), 400
        occ.unit_id = unit_id
    # If only changing dates, check for overlap in current unit
    else:
        overlap = Occupancy.query.filter(
            Occupancy.unit_id == occ.unit_id,
            Occupancy.id != id,
            Occupancy.move_in_date < (move_out_dt or date.max),
            or_(Occupancy.move_out_date == None, Occupancy.move_out_date > move_in_dt)
        ).first()
        if overlap:
            return jsonify({'error': 'Unit is already occupied during the specified period'}), 400
    occ.move_in_date = move_in_dt
    occ.move_out_date = move_out_dt
    db.session.commit()
    return jsonify(occ.to_dict()), 200
