from flask import request, jsonify, Blueprint
from .. import db
from ..models import Property, Unit

properties_bp = Blueprint('properties', __name__)

@properties_bp.route('/properties', methods=['POST'])
def create_property():
    data = request.json
    if not data or not data.get('name'):
        return jsonify({'error': 'Property name is required'}), 400
    
    prop = Property(name=data['name'])
    db.session.add(prop)
    db.session.commit()
    return jsonify(prop.to_dict()), 201

@properties_bp.route('/properties', methods=['GET'])
def get_properties():
    props = Property.query.all()
    return jsonify([p.to_dict() for p in props]), 200

@properties_bp.route('/properties/<int:id>', methods=['GET'])
def get_property(id):
    prop = db.session.get(Property, id)
    if not prop:
        return jsonify({'error': 'Property not found'}), 404
    return jsonify(prop.to_dict()), 200

@properties_bp.route('/properties/<int:id>/units', methods=['GET'])
def get_property_units(id):
    prop = db.session.get(Property, id)
    if not prop:
        return jsonify({'error': 'Property not found'}), 404

    units = Unit.query.filter_by(property_id=id).all()
    return jsonify([u.to_dict() for u in units]), 200
