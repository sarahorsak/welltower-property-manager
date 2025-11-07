from flask import Blueprint, request, jsonify
from ..models import Occupancy, Unit, Resident, Rent
from .. import db
from sqlalchemy import or_
from datetime import date

occupancy_bp = Blueprint('occupancy', __name__)

@occupancy_bp.route('/occupancy/move-in', methods=['POST'])
def move_in():
    data = request.json
    required_fields = ['resident_id', 'unit_id', 'move_in_date', 'initial_rent']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing fields'}), 400
    move_in_dt = date.fromisoformat(data['move_in_date'])
    unit = Unit.query.get(data['unit_id'])
    if not unit:
        return jsonify({'error': 'Unit not found'}), 404
    if unit.get_status_on_date(move_in_dt) == 'inactive':
        return jsonify({'error': f'Unit {unit.unit_number} is inactive on {move_in_dt.isoformat()}'}), 400
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
    rent = Rent(
        occupancy=occ,
        amount=data['initial_rent'],
        effective_date=move_in_dt
    )
    db.session.add(rent)
    db.session.commit()
    return jsonify({'message': 'Move-in successful', 'occupancy_id': occ.id}), 201

@occupancy_bp.route('/occupancy/<int:id>/move-out', methods=['PUT'])
def move_out(id):
    data = request.json
    if not data or not data.get('move_out_date'):
        return jsonify({'error': 'move_out_date is required'}), 400
    occ = Occupancy.query.get(id)
    if not occ:
        return jsonify({'error': 'Occupancy record not found'}), 404
    move_out_dt = date.fromisoformat(data['move_out_date'])
    if move_out_dt < occ.move_in_date:
        return jsonify({'error': 'Move-out date must be on or after move-in date.'}), 400
    occ.move_out_date = move_out_dt
    db.session.commit()
    return jsonify({'message': 'Move-out successful'}), 200

@occupancy_bp.route('/occupancy/<int:id>/rent-change', methods=['POST'])
def rent_change(id):
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
    rent = Rent(
        occupancy_id=occ.id,
        amount=data['new_rent'],
        effective_date=eff_date
    )
    db.session.add(rent)
    db.session.commit()
    return jsonify({'message': 'Rent change logged', 'rent_id': rent.id}), 201

@occupancy_bp.route('/occupancy/<int:id>/rents', methods=['GET'])
def occupancy_rents(id):
    occ = Occupancy.query.get(id)
    if not occ:
        return jsonify({'error': 'Occupancy not found'}), 404
    rents = Rent.query.filter_by(occupancy_id=id).order_by(Rent.effective_date).all()
    return jsonify([{'id': r.id, 'amount': r.amount, 'effective_date': r.effective_date.isoformat()} for r in rents]), 200

@occupancy_bp.route('/occupancies', methods=['GET'])
def list_occupancies():
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
