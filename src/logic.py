"""
Compatibility shim: export the service implementations from the new `services` package.
This keeps `from .logic import generate_rent_roll` working while the codebase migrates.
"""
"""
Compatibility shim: export the service implementations from the new `services` package.
This keeps `from .logic import generate_rent_roll` working while the codebase migrates.
"""
from .services.rent_roll import generate_rent_roll
from .services.kpis import calculate_kpis

__all__ = ['generate_rent_roll', 'calculate_kpis']