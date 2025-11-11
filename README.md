# Welltower Property Manager

## Project Overview & Business Context

Welltower Property Manager is a backend system for managing multifamily commercial real estate properties. It enables property managers and operators to track properties, units, residents, occupancy, rent changes, and generate operational and financial reports such as rent rolls and KPIs. The system is designed to reflect real-world property management workflows, supporting daily operations and strategic decision-making.

**Business Value:**
- Provides a single source of truth for property, unit, and resident data.
- Automates rent roll and occupancy reporting, saving time and reducing errors.
- Supports compliance and business analysis with robust data validation and auditability.
- Enables better revenue management and operational efficiency through clear reporting and configurable business rules.

## How to Run This Project

This project runs on macOS, Linux, and Windows (with WSL or native Python). You can use Python directly or Docker.

### 1. Python (Recommended for Local Development)

**Prerequisites:**

- Python 3.9+ and pip
- (Recommended) Virtual environment tool: `venv` or `virtualenv`

1. **Download and unzip the repository archive:**
	```sh
	# macOS / Linux / WSL
	unzip welltower-property-manager.zip
	cd welltower-property-manager
	```

	Or on Windows (PowerShell):
	```powershell
	# PowerShell (Windows)
	Expand-Archive -Path .\welltower-property-manager.zip -DestinationPath .
	Set-Location .\welltower-property-manager
	```
2. **Create and activate a virtual environment:**
	```sh
	python3 -m venv venv
	source venv/bin/activate  # On Windows: venv\Scripts\activate
	```
3. **Install dependencies:**
	```sh
	pip install -r requirements.txt
	```
4. **Run the application:**
	```sh
	flask --app src:create_app --debug run
	```
5. **Run tests:**
	```sh
	pytest
	```

### 2. Docker (Optional)

**Prerequisite:**
- Docker and Docker Compose installed ([Download Docker](https://www.docker.com/get-started/))

Use the following command from the project root: 
```sh
docker-compose up --build
```

Once running, the API will be available at http://localhost:5000/

To stop the containers, press Ctrl+C in the terminal, then run:

```sh
docker-compose down
```

---

# Welltower Property Manager

# API Endpoints

This API provides endpoints for managing properties, units, residents, occupancies, and generating reports. All endpoints return JSON unless otherwise noted.

### Properties
- `POST /properties` — Create a property
- `GET /properties` — List all properties
- `GET /properties/<id>` — Get property details
- `PATCH /properties/<id>` — Update property details
- `GET /properties/<id>/units` — List units in a property

### Units
- `POST /units` — Create a unit
- `GET /units` — List all units (optionally by property)
- `GET /units/<id>` — Get unit details
- `PATCH /units/<id>` — Update unit details (unit_number, property_id)
- `POST /units/<id>/status` — Set unit status (active/inactive)
- `GET /units/<id>/status` — Get unit status (optionally by date)

### Residents
- `POST /residents` — Create a resident
- `GET /residents` — List all residents (optionally by property)
- `GET /residents/<id>` — Get resident details
- `PATCH /residents/<id>` — Update resident details

### Occupancy
- `POST /occupancy/move-in` — Move a resident into a unit
- `PUT /occupancy/<id>/move-out` — Move a resident out
- `PATCH /occupancy/<id>` — Update occupancy (move-in/move-out dates, unit assignment)
- `POST /occupancy/<id>/rent-change` — Change rent for an occupancy
- `GET /occupancy/<id>/rents` — List rent history for an occupancy
- `GET /occupancies` — List all occupancies

### Reports
- `GET /reports/rent-roll?property_id=...&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` — Generate rent roll
- `GET /reports/kpi-move?property_id=...&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` — Move-in/move-out counts
- `GET /reports/kpi-occupancy?property_id=...&year=YYYY&month=MM` — Occupancy rate for a month

### Admin Page
- `/admin` — Simple web admin interface for managing properties, units, and residents.
	- Touches: `/properties`, `/units`, `/residents` endpoints for CRUD operations.
	- Allows: Creating, editing, and viewing properties, units, and residents from a browser UI.


## Assumptions & Data Validations

- All core data validations (e.g., unit number format, min/max values, name patterns) are defined in `src/config.py` via the `ValidationConfig` class. You can alter these validation rules without editing the route logic.
- Units cannot be set to inactive if occupied or if a future occupancy is scheduled.
- Move-in date must be before move-out date (if both are provided).
- Duplicate rent records (same occupancy, date, and amount) are not allowed.
- Residents cannot move into inactive units.
- The rent roll always shows all units (active/inactive, vacant/occupied) for every day in the range.
- All endpoints validate required fields and return clear error messages.

## Testing Strategy

- Comprehensive unit and integration tests using pytest.
- Edge cases for overlapping occupancies, rent changes, unit status, and KPI calculations are covered.
- Tests ensure that business rules and data validations are enforced.


## Thought Process & Reviewability

- Code is organized by feature (routes, services, models) for clarity and maintainability.
- Service layer encapsulates business logic, making it easy to test and extend.
- Data model and endpoints are designed to reflect real-world property management needs.
- All validation rules are centralized in the `ValidationConfig` class in `src/config.py`, so business rules can be updated in one place without touching the route code.
- The `/admin` page provides a simple web interface for CRUD operations on properties, units, and residents, making it easier for non-technical users to interact with the system. It directly uses the `/properties`, `/units`, and `/residents` API endpoints for all data operations.


## Enhancements & Follow-ons (If I Had More Time)

- Add authentication and user roles so different users (like admins and property managers) have the right access and permissions.
- Make it easier to browse and search large lists of properties, units, and residents by adding pagination and filtering.
- Allow deleted records to be recovered and keep a history of all changes for better accountability.
- Provide more detailed reports, such as revenue, delinquency, and resident history, to help with business decisions.
- Build a more interactive and visually appealing web dashboard for users to manage data and view reports.
- Offer clear, interactive API documentation for easier integration and onboarding.
- Support importing and exporting data in bulk (CSV, Excel) to make onboarding and reporting easier.
- Add more detailed permissions and track user activity for security and compliance.
- Allow configuration of default or property-specific percentage rent increases to automate annual adjustments.
- Track unit types (like studio, 1BR, 2BR) and whether a unit is renovated or not, for better reporting and pricing.
- Add support for "model units" (units used for tours, not available for rent).
- Add visual dashboards with pie charts and diagrams to help users quickly understand occupancy, rent mix, and other key metrics.

## Shortcomings

- Some edge cases and advanced reporting features are not implemented due to time.
- UI is basic and not fully reactive.
- No authentication or user management.


## Additional API Read Endpoints

The project also provides standard GET/read endpoints to make the API discoverable and easy to inspect:

- GET /properties -> list all properties
- GET /properties/<id> -> property detail
- GET /properties/<id>/units -> list units in a property
- GET /units -> list all units (optional ?property_id=)
- GET /units/<id> -> unit detail (includes current_status when available)
- GET /residents -> list residents (optional ?property_id=)
- GET /residents/<id> -> resident detail (includes current occupancy when present)
- GET /occupancy/<id>/rents -> rent history for an occupancy

These endpoints are covered by integration tests in `tests/test_api.py` (see `test_get_endpoints_list_and_detail` and `test_occupancy_rents_history_endpoint`).

## Quick Examples

Create a property (POST):

```bash
curl -sS -X POST http://127.0.0.1:5000/properties \
	-H "Content-Type: application/json" \
	-d '{"name":"Sunset Gardens"}' | jq
```

Get all properties (GET):

```bash
curl -sS http://127.0.0.1:5000/properties | jq
```

Get rent history for an occupancy (GET):

```bash
curl -sS http://127.0.0.1:5000/occupancy/1/rents | jq
```

## Running tests (reminder)

Run the full test suite from project root:

```bash
pytest -q
```

Run only API tests:

```bash
pytest tests/test_api.py -q
```
