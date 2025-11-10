# src/models.py
from . import db
from datetime import date
from sqlalchemy import desc

class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    units = db.relationship('Unit', back_populates='property', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'unit_count': self.units.count()
        }

class Unit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    unit_number = db.Column(db.String(50), nullable=False)
    
    property = db.relationship('Property', back_populates='units')
    occupancies = db.relationship('Occupancy', back_populates='unit', lazy='dynamic')
    status_history = db.relationship('UnitStatus', back_populates='unit', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'property_id': self.property_id,
            'unit_number': self.unit_number
        }
        
    def get_status_on_date(self, on_date):
            """Finds the unit's status on a specific date (Unit Status Stretch Goal)."""
            # Find the MOST RECENT status_history record where start_date <= on_date
            status = self.status_history.filter(UnitStatus.start_date <= on_date) \
                                    .order_by(UnitStatus.start_date.desc()) \
                                    .first()
            return status.status if status else 'active' # Default to active

class Resident(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    occupancies = db.relationship('Occupancy', back_populates='resident', lazy='dynamic')

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def to_dict(self):
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name
        }

class Occupancy(db.Model):
    def to_dict(self):
        return {
            'id': self.id,
            'unit_id': self.unit_id,
            'resident_id': self.resident_id,
            'move_in_date': self.move_in_date.isoformat() if self.move_in_date else None,
            'move_out_date': self.move_out_date.isoformat() if self.move_out_date else None
        }
    
    """Links a Resident to a Unit for a period of time."""
    id = db.Column(db.Integer, primary_key=True)
    unit_id = db.Column(db.Integer, db.ForeignKey('unit.id'), nullable=False)
    resident_id = db.Column(db.Integer, db.ForeignKey('resident.id'), nullable=False)
    
    move_in_date = db.Column(db.Date, nullable=False)
    move_out_date = db.Column(db.Date, nullable=True) # null means currently occupied

    unit = db.relationship('Unit', back_populates='occupancies')
    resident = db.relationship('Resident', back_populates='occupancies')
    rent_history = db.relationship('Rent', back_populates='occupancy', 
                                   order_by='Rent.effective_date', lazy='dynamic')

    def get_rent_on_date(self, target_date):
        rent_record = Rent.query.filter(
            Rent.occupancy_id == self.id,
            Rent.effective_date <= target_date
        ).order_by(desc(Rent.effective_date)).first()

        return rent_record.amount if rent_record else 0

class Rent(db.Model):
    def to_dict(self):
        return {
            'id': self.id,
            'occupancy_id': self.occupancy_id,
            'amount': self.amount,
            'effective_date': self.effective_date.isoformat() if self.effective_date else None
        }
    
    """Tracks rent changes over time for a specific occupancy."""
    id = db.Column(db.Integer, primary_key=True)
    occupancy_id = db.Column(db.Integer, db.ForeignKey('occupancy.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False) 
    effective_date = db.Column(db.Date, nullable=False)

    occupancy = db.relationship('Occupancy', back_populates='rent_history')

class UnitStatus(db.Model):
    def to_dict(self):
        return {
            'id': self.id,
            'unit_id': self.unit_id,
            'status': self.status,
            'start_date': self.start_date.isoformat() if self.start_date else None
        }
    """(Stretch Goal) Tracks unit status changes."""
    id = db.Column(db.Integer, primary_key=True)
    unit_id = db.Column(db.Integer, db.ForeignKey('unit.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='active') # 'active' | 'inactive'
    start_date = db.Column(db.Date, nullable=False)
    
    unit = db.relationship('Unit', back_populates='status_history')