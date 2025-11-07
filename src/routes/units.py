from flask import Blueprint, request, jsonify
from ..models import Property, Unit, UnitStatus, Occupancy, Resident, Rent
from .. import db
from datetime import date

units_bp = Blueprint('units', __name__)

@units_bp.route('/units', methods=['POST'])
def create_unit():
    data = request.json
    if not data or not data.get('property_id') or not data.get('unit_number'):
        return jsonify({'error': 'property_id and unit_number are required'}), 400
    prop = db.session.get(Property, data['property_id'])
    if not prop:
        return jsonify({'error': 'Property not found'}), 404
    unit = Unit(property_id=data['property_id'], unit_number=data['unit_number'])
    db.session.add(unit)
    db.session.commit()
    return jsonify(unit.to_dict()), 201

@units_bp.route('/units', methods=['GET'])
def list_units():
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

@units_bp.route('/units/<int:id>', methods=['GET'])
def get_unit(id):
    unit = db.session.get(Unit, id)
    if not unit:
        return jsonify({'error': 'Unit not found'}), 404
    data = unit.to_dict()
    try:
        data['current_status'] = unit.get_status_on_date(date.today())
    except Exception:
        pass
    return jsonify(data), 200

@units_bp.route('/units/<int:id>/status', methods=['POST'])
def set_unit_status(id):
    data = request.json
    required_fields = ['status', 'start_date']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing status or start_date'}), 400
    unit = db.session.get(Unit, id)
    if not unit:
        return jsonify({'error': 'Unit not found'}), 404
    try:
        start_dt = date.fromisoformat(data['start_date'])
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    if data['status'] not in ['active', 'inactive']:
        return jsonify({'error': 'Status must be "active" or "inactive"'}), 400
    if UnitStatus.query.filter_by(unit_id=id, start_date=start_dt).first():
        return jsonify({'error': f'A status change already exists for unit {id} on {start_dt}'}), 400
    # Prevent setting to inactive if occupied on start_dt
    if data['status'] == 'inactive':
        occ = Occupancy.query.filter(
            Occupancy.unit_id == id,
            Occupancy.move_in_date <= start_dt,
            (Occupancy.move_out_date == None) | (Occupancy.move_out_date > start_dt)
        ).first()
        if occ:
            return jsonify({'error': 'Cannot set unit to inactive while it is occupied.'}), 400
    status_rec = UnitStatus(
        unit_id=id,
        status=data['status'],
        start_date=start_dt
    )
    db.session.add(status_rec)
    db.session.commit()
    return jsonify({'message': 'Unit status change logged'}), 201

@units_bp.route('/units/<int:id>/status', methods=['GET'])
def get_unit_status(id):
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
    current_status = unit.get_status_on_date(date.today())
    history = []
    for s in unit.status_history.order_by(UnitStatus.start_date).all():
        history.append({'id': s.id, 'status': s.status, 'start_date': s.start_date.isoformat()})
    return jsonify({'unit_id': id, 'current_status': current_status, 'history': history}), 200

@units_bp.route('/units/<int:unit_id>/rents', methods=['GET'])
def unit_rents(unit_id):
    unit = db.session.get(Unit, unit_id)
    if not unit:
        return jsonify({'error': 'Unit not found'}), 404
    occs = unit.occupancies.order_by(Occupancy.move_in_date).all()
    out = []
    for occ in occs:
        resident = occ.resident
        rents = Rent.query.filter_by(occupancy_id=occ.id).order_by(Rent.effective_date).all()
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
