from flask import Blueprint, request, jsonify, Response
from ..services.rent_roll import generate_rent_roll
from ..services.kpis import move_in_out_counts, occupancy_rate_for_month
from datetime import date
import csv
import io

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/reports/rent-roll', methods=['GET'])
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
    if end_dt < start_dt:
        return jsonify({'error': 'End date must be on or after start date.'}), 400
    rent_roll_data = generate_rent_roll(prop_id, start_dt, end_dt)
    fmt = request.args.get('format')
    if fmt == 'csv':
        output = io.StringIO()
        writer = None
        for row in rent_roll_data:
            if writer is None:
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


# Move-in/out counts for a date range
@reports_bp.route('/reports/kpi-move', methods=['GET'])
def get_kpi_move():
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
    result = move_in_out_counts(prop_id, start_dt, end_dt)
    return jsonify(result), 200

# Occupancy rate for a given month
@reports_bp.route('/reports/kpi-occupancy', methods=['GET'])
def get_kpi_occupancy():
    property_id = request.args.get('property_id')
    year = request.args.get('year')
    month = request.args.get('month')
    if not all([property_id, year, month]):
        return jsonify({'error': 'property_id, year, and month are required'}), 400
    try:
        prop_id = int(property_id)
        year = int(year)
        month = int(month)
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid year/month/property_id'}), 400
    if not (1 <= month <= 12):
        return jsonify({'error': 'Month must be between 1 and 12'}), 400
    if year < 1:
        return jsonify({'error': 'Year must be a positive integer'}), 400
    result = occupancy_rate_for_month(prop_id, year, month)
    return jsonify(result), 200
