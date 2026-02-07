Name: Navid Ziran
JHED ID: nziran1
Module Info: Module 3 — GradCafe Database + Flask Analysis Dashboard
Due Date: 2/8/2026

SSH Repo URL: git@github.com:nziran/jhu_software_concepts.git

⸻

This project builds a complete pipeline that scrapes GradCafe applicant data, 
cleans and loads it into PostgreSQL, and displays analytics through a Flask web interface. 
It also includes dynamic controls that allow users to pull new data and refresh analysis in real time.

The system is divided into Part A (core pipeline + static analysis) and Part B (dynamic update controls).

The initial database is seeded from the scraped and cleaned file llm_extend_applicant_data.json 
(originally produced in Module 2 and included here for reproducibility).
The repository includes the initial dataset required to seed the database,
making the assignment fully reproducible without external files.

This file is loaded via load_data.py to the PostgreSQL database called gradcafe, table applicants.

The Flask dashboard triggers a background pipeline that scrapes, cleans, 
and loads new GradCafe records using scrape_update.py, clean_update.py, and load_update.py

The data is then analyzed using query_data.py.

⸻

Requirements

• Python 3.10+ (tested on Python 3.12 and 3.14)
• PostgreSQL running locally

⸻

Dependencies Used

• Flask — web framework for the analysis dashboard
• psycopg — PostgreSQL database connectivity
• beautifulsoup4 — HTML parsing during scraping

All Python dependencies and compatibility are listed in requirements.txt.

⸻

Setup and Run Instructions

	1. Create and activate a virtual environment:

   		python3 -m venv .venv
   		source .venv/bin/activate

	2. Install dependencies:

   		pip install -r requirements.txt

		Important: All commands below should be run from inside the module_3 folder.
			
	3.  PostgreSQL setup (required)

			- PostgreSQL role (username): ziran
			- PostgreSQL database: gradcafe
			- No password (local trust/peer auth)

			- If your Postgres requires a password, set one for role ziran and 
			  update DB connection settings accordingly

	4.  Start PostgreSQL (Homebrew):

   			brew services start postgresql@16

	5.  Create the role/user:

   			createuser -s ziran

			If the role or database already exists, PostgreSQL will report an error.
			This is safe to ignore.

	6.  Create the database owned by that user:

   			createdb -O ziran gradcafe

			If the database already exists, PostgreSQL will report an error - this is safe to ignore.

	7.  Verify database connection:

   			psql -U ziran -d gradcafe -c "SELECT 1;"

			Expected output: 
			
			?column?
			----------
			1

⸻


━━━━━━━━━━━━━━━━━━━━
PART A — Core Pipeline + Flask Dashboard (Required Steps)
━━━━━━━━━━━━━━━━━━━━

Part A prepares the database and launches the analysis dashboard. These steps are required for the application to run.

⸻

Step A1 — Seed the database

File: load_data.py

This script:

• Creates the applicants table if it does not already exist
• Loads the bundled dataset llm_extend_applicant_data.json
• Inserts all records into PostgreSQL

This step initializes the database used by the dashboard.

Run:

python load_data.py

You should see a message confirming rows were inserted.

⸻

Step A2 — Launch the Flask dashboard

Run:

python app.py

Open your browser and navigate to:

http://127.0.0.1:5000/analysis

The dashboard will display analytics based on the seeded database.

⸻

Important — Automated pipeline behavior

The application includes a full scrape → clean → load pipeline:

scrape_update.py
clean_update.py
load_update.py

These scripts are executed automatically by the Flask dashboard when the Pull Data button is pressed.  
Database updates occur immediately, but analysis results only refresh when the Update Analysis button is pressed.
Thus, manual execution of these scripts is not required to run the dashboard.

⸻

━━━━━━━━━━━━━━━━━━━━
PART B — Dynamic Update Controls
━━━━━━━━━━━━━━━━━━━━

Part B adds interactive controls allowing users to update the database and refresh analysis directly from the webpage.

⸻

Step B1 — Pull Data Button

Button label: Pull Data

When pressed:

• Executes scrape_update.py → clean_update.py → load_update.py
• Runs in a background subprocess pipeline
• Prevents duplicate scraping
• Displays status messages
• Temporarily blocks conflicting actions

Users receive feedback while the pipeline runs and see completion status when finished.

⸻

Step B2 — Update Analysis Button

Button label: Update Analysis

When pressed:

• Refreshes analysis queries using the latest database state
• Updates the analysis timestamp
• Does nothing if a Pull Data job is running
• Displays a notification explaining why refresh is blocked
• Database updates occur immediately, but dashboard analysis 
  results only change when “Update Analysis” is pressed.

This ensures analysis always reflects the newest dataset.

⸻

How Part B Works Internally

app.py manages background execution using:

• subprocess pipelines
• thread locking
• job state tracking
• UI messaging

The webpage auto-refreshes while data pulls are running so users can observe progress.

⸻

Data Flow Overview

GradCafe website
→ scrape_update.py
→ clean_update.py
→ load_update.py
→ PostgreSQL database
→ query_data.py
→ Flask dashboard

Dynamic controls allow repeating this pipeline without restarting the application.

⸻

Known Limitations / Troubleshooting

• Some GradCafe entries lack GPA/GRE or start-term data
• Occasional network timeouts may skip detail pages
• Missing fields are stored as None to preserve dataset consistency
• If Pull Data reports “0 rows inserted,” this means the database is already up to date.
  The scraper only adds new GradCafe entries and safely skips duplicates.
• Pull Data updates the database only. Analysis results do NOT change until
  the “Update Analysis” button is pressed. This behavior is intentional.
• If scraping fails with an SSL CERTIFICATE_VERIFY_FAILED error on macOS:

  		Upgrade certificates by running:

      		pip install --upgrade certifi
      		/Applications/Python\ 3.12/Install\ Certificates.command

  Then restart the application.

⸻

Summary

This project implements:

• Web scraping pipeline
• Data normalization
• PostgreSQL integration
• Flask analytics dashboard
• Dynamic update controls

The result is a reproducible, database-backed analytics system that 
supports live updates through a browser interface.