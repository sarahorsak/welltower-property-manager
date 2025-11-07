from flask import Blueprint, request, jsonify
from ..models import Resident, Occupancy, Unit
from .. import db

residents_bp = Blueprint('residents', __name__)

@residents_bp.route('/residents', methods=['POST'])
def create_resident():
    data = request.json
    if not data or not data.get('first_name') or not data.get('last_name'):
        return jsonify({'error': 'first_name and last_name are required'}), 400
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
    res = Resident.query.get(id)
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
