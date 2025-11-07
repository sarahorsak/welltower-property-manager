# Register all blueprints here
def register_blueprints(app):
    from .properties import properties_bp
    from .units import units_bp
    from .residents import residents_bp
    from .occupancy import occupancy_bp
    from .reports import reports_bp
    from .admin import admin_bp

    app.register_blueprint(properties_bp)
    app.register_blueprint(units_bp)
    app.register_blueprint(residents_bp)
    app.register_blueprint(occupancy_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(admin_bp)
