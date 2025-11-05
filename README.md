🏢 Welltower Backend Engineering Assessment
Property Management API
This project delivers a robust backend solution for a senior living property management system, focusing on accurate historical financial reporting (Rent Roll) and core entity management. It is built using Python, Flask, and SQLAlchemy, packaged with Docker for guaranteed cross-platform compatibility.

Feature	Status	Notes
Data Modeling	Complete	Decoupled time-series model for historical accuracy.
Rent Roll Report	Complete	Generates daily rent and occupancy snapshots over a date range.
API Validations	Complete	Implements critical business rules (e.g., preventing unit double-booking).
Unit Status (Stretch)	Implemented	Logic accounts for unit active/inactive status changes over time.
KPI Report (Stretch)	Implemented	Calculates Occupancy Rate, Move-ins, and Move-outs based on Rent Roll data.
Testing	Comprehensive	Unit and Integration tests cover all core logic and APIs.

🧠 Architectural & Data Model Thought Process
The core challenge is handling data that changes over time (rent increases, move-ins/outs) to generate reports for any date in the past. This requires a time-series data model.

1. Relational Time-Series Design
Instead of updating a single field (e.g., unit.current_rent), historical events are recorded in separate tables:

Occupancy: Links a Resident to a Unit with explicit move_in_date and move_out_date. This table defines the tenancy period.

Rent: Stores a series of rent amounts, each with an effective_date. The actual rent on any given day is the last recorded amount whose effective_date is on or before that day.

UnitStatus: (Stretch) Tracks when a unit's status (active/inactive) changes, preserving the historical availability.

This approach ensures perfect historical accuracy for auditing and financial reports.

2. Rent Roll Logic Flow (src/logic.py)
The generate_rent_roll function operates on the principle of state aggregation:

It iterates through every day in the requested date range.

For each day and each unit, it performs database lookups against the time-series tables:

What is the Unit Status today?

Is there an Occupancy record active today?

If occupied, what is the effective Rent today?

This daily state is compiled into the final report structure. The KPI API (calculate_kpis) then consumes this daily report to calculate monthly metrics.

🚀 How to Run and Test the Project
Docker is the recommended method as it guarantees the correct Python, dependency, and database configuration, providing the most reliable environment for code review.

Method 1: Docker (Recommended) 🐳
This method builds the application, runs the complete test suite, and starts the server in one command.

Prerequisites: Docker Desktop installed and running.

Execute from Root Directory: Open your terminal in the project's root folder (containing Dockerfile and docker-compose.yml) and run:

Bash

docker-compose up --build
Verify Tests: The first output will be the execution of the full pytest suite. All tests must PASS before the server starts.

Access the API: The Flask application will be running and accessible at: http://127.0.0.1:5000

Method 2: Local Environment
Prerequisites: Python 3.8+, pip, and venv.

Setup Virtual Environment:

Bash

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
Run Tests:

Bash

pytest
Run Server:

Bash

flask --app src:create_app --debug run
🔌 Core API Endpoints
The base URL is http://127.0.0.1:5000.

1. Management
Endpoint	Method	Purpose
/properties	POST	Create a new property.
/units	POST	Create a new unit.
/residents	POST	Create a new resident profile.
/units/<id>/status	POST	Log a unit status change (e.g., {"status": "inactive", "start_date": "YYYY-MM-DD"}).

2. Occupancy & Rent
Endpoint	Method	Purpose
/occupancy/move-in	POST	Starts a new tenancy, performs double-booking/inactive unit validations.
/occupancy/<id>/move-out	PUT	Ends a tenancy by setting the move_out_date.
/occupancy/<id>/rent-change	POST	Logs a new rent amount with an effective_date.

3. Reporting
Endpoint	Method	Description
/reports/rent-roll	GET	Core Report: Generates a daily snapshot of occupancy, rent, and status for a property over a date range.
/reports/kpi	GET	KPI Stretch Goal: Summarizes monthly metrics (Occupancy Rate, Move-ins, Move-outs).

Example: Get Rent Roll

Bash

curl -X GET "http://127.0.0.1:5000/reports/rent-roll?property_id=1&start_date=2024-01-01&end_date=2024-01-31"
🛠️ Project Structure
.
├── src/                    # Contains the actual application code
│   ├── __init__.py         # Flask App and Database initialization (App Factory)
│   ├── models.py           # SQLAlchemy Models and data helpers
│   ├── routes.py           # API endpoints and input validation
│   └── logic.py            # Business logic (Rent Roll & KPI calculation)
├── tests/                  # All testing files
│   ├── conftest.py         # Pytest fixtures (DB setup)
│   ├── test_api.py         # Integration tests (via API endpoints)
│   └── test_logic.py       # Unit tests (direct logic function calls)
├── requirements.txt
├── README.md
├── Dockerfile
└── docker-compose.yml