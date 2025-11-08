from flask import Blueprint, request, jsonify
from ..models import Resident, Occupancy, Unit
from ..config import ValidationConfig
from .. import db
import re

residents_bp = Blueprint('residents', __name__)

@residents_bp.route('/residents', methods=['POST'])
def create_resident():
    data = request.json
    if not data or not data.get('first_name') or not data.get('last_name'):
        return jsonify({'error': 'first_name and last_name are required'}), 400
    # Validate name format and length
    for field in ['first_name', 'last_name']:
        val = data[field]
        if not re.match(ValidationConfig.RESIDENT_NAME_REGEX, val):
            return jsonify({'error': f'{field} must match pattern {ValidationConfig.RESIDENT_NAME_REGEX}'}), 400
        if len(val) > ValidationConfig.RESIDENT_NAME_MAX_LENGTH:
            return jsonify({'error': f'{field} max length is {ValidationConfig.RESIDENT_NAME_MAX_LENGTH}'}), 400
    # Enforce unique first+last name if configured
    q = Resident.query
    if ValidationConfig.ENFORCE_UNIQUE_RESIDENT_NAME:
        if ValidationConfig.ENFORCE_UNIQUE_RESIDENT_NAME_CASE_INSENSITIVE:
            q = q.filter(db.func.lower(Resident.first_name) == data['first_name'].lower(), db.func.lower(Resident.last_name) == data['last_name'].lower())
        else:
            q = q.filter_by(first_name=data['first_name'], last_name=data['last_name'])
        exists = q.first()
        if exists:
            return jsonify({'error': 'Resident with this first and last name already exists'}), 400
    res = Resident(first_name=data['first_name'], last_name=data['last_name'])
    db.session.add(res)
    db.session.commit()
    return jsonify(res.to_dict()), 201

@residents_bp.route('/residents', methods=['GET'])
def list_residents():
    property_id = request.args.get('property_id')
    if property_id:
        try:
            pid = int(property_id)
        except ValueError:
            return jsonify({'error': 'property_id must be an integer'}), 400
        residents = Resident.query.join(Occupancy, isouter=True).join(Unit, isouter=True).filter(Unit.property_id == pid).all()
    else:
        residents = Resident.query.all()
    return jsonify([r.to_dict() for r in residents]), 200

@residents_bp.route('/residents/<int:id>', methods=['GET'])
def get_resident(id):
    res = db.session.get(Resident, id)
    if not res:
        return jsonify({'error': 'Resident not found'}), 404
    data = res.to_dict()
    try:
        occ = Occupancy.query.filter_by(resident_id=res.id, move_out_date=None).first()
        if occ:
            data['current_occupancy'] = occ.to_dict()
    except Exception:
        pass
    return jsonify(data), 200


# PATCH endpoint to amend resident details
@residents_bp.route('/residents/<int:id>', methods=['PATCH'])
def update_resident(id):
    data = request.json
    res = db.session.get(Resident, id)
    if not res:
        return jsonify({'error': 'Resident not found'}), 404
    import re
    new_first = data.get('first_name', res.first_name)
    new_last = data.get('last_name', res.last_name)
    for field, val in [('first_name', new_first), ('last_name', new_last)]:
        if not re.match(ValidationConfig.RESIDENT_NAME_REGEX, val):
            return jsonify({'error': f'{field} must match pattern {ValidationConfig.RESIDENT_NAME_REGEX}'}), 400
        if len(val) > ValidationConfig.RESIDENT_NAME_MAX_LENGTH:
            return jsonify({'error': f'{field} max length is {ValidationConfig.RESIDENT_NAME_MAX_LENGTH}'}), 400
    q = Resident.query.filter(Resident.id != id)
    if ValidationConfig.ENFORCE_UNIQUE_RESIDENT_NAME:
        if ValidationConfig.ENFORCE_UNIQUE_RESIDENT_NAME_CASE_INSENSITIVE:
            q = q.filter(db.func.lower(Resident.first_name) == new_first.lower(), db.func.lower(Resident.last_name) == new_last.lower())
        else:
            q = q.filter_by(first_name=new_first, last_name=new_last)
        exists = q.first()
        if exists:
            return jsonify({'error': 'Resident with this first and last name already exists'}), 400
    if 'first_name' in data:
        res.first_name = data['first_name']
    if 'last_name' in data:
        res.last_name = data['last_name']
    db.session.commit()
    return jsonify(res.to_dict()), 200
