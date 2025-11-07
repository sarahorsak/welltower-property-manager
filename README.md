docker-compose up --build
curl -X GET "http://127.0.0.1:5000/reports/rent-roll?property_id=1&start_date=2024-01-01&end_date=2024-01-31"

# Welltower Property Manager

## Setup & Running

1. **Clone the repository:**
	```sh
	git clone <repo-url>
	cd welltower-property-manager
	```
2. **Install dependencies:**
	```sh
	pip install -r requirements.txt
	```
3. **Run the application:**
	```sh
	flask --app src:create_app --debug run
	```
4. **(Optional) Run with Docker:**
	```sh
	docker-compose up --build
	```
5. **Run tests:**
	```sh
	pytest
	```

## API Endpoints

### Properties
- `POST /properties` — Create a property
- `GET /properties` — List all properties

### Units
- `POST /units`  Create a unit
- `GET /units`  List all units (optionally by property)
- `GET /units/<id>`  Get unit details
- `PATCH /units/<id>`  Update unit details (unit_number, property_id)
- `POST /units/<id>/status`  Set unit status (active/inactive)
- `GET /units/<id>/status`  Get unit status (optionally by date)

### Residents
- `POST /residents`  Create a resident
- `GET /residents`  List all residents
- `PATCH /residents/<id>`  Update resident details

### Occupancy
- `POST /occupancy/move-in`  Move a resident into a unit
- `PUT /occupancy/<id>/move-out`  Move a resident out
- `PATCH /occupancy/<id>`  Update occupancy (move-in/move-out dates, unit assignment)
- `POST /occupancy/<id>/rent-change`  Change rent for an occupancy
- `GET /occupancy/<id>/rents`  List rent history for an occupancy
- `GET /occupancies`  List all occupancies

### Reports
- `GET /reports/rent-roll?property_id=...&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` — Generate rent roll
- `GET /reports/kpi-move?property_id=...&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` — Move-in/move-out counts
- `GET /reports/kpi-occupancy?property_id=...&year=YYYY&month=MM` — Occupancy rate for a month

## Assumptions & Data Validations

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

## Enhancements & Follow-ons (If I Had More Time)

- Add authentication and user roles (admin, property manager, etc).
- Add pagination and filtering to list endpoints.
- Add soft-deletion and audit logging for all changes.
- Add richer reporting (e.g., revenue, delinquency, resident history).
- Add a more dynamic frontend (React/Vue) for a better user experience.
- Add OpenAPI/Swagger documentation for all endpoints.
- Add support for bulk data import/export (CSV, Excel).
- Add more granular permissions and activity tracking.

## Shortcomings

- Some edge cases and advanced reporting features are not implemented due to time constraints.
- UI is basic and not fully reactive.
- No authentication or user management.

---
If you have questions or want to discuss design decisions, please reach out!

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
