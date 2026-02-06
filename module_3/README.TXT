Name: Navid Ziran
JHED ID: nziran1
Module Info: Module 3 — GradCafe Database + Flask Analysis Dashboard
Due Date: 2/8/2026

SSH Repo URL: git@github.com:nziran/jhu_software_concepts.git

⸻

This project builds a complete pipeline that scrapes GradCafe applicant data, cleans and loads it into PostgreSQL, and displays analytics through a Flask web interface. It also includes dynamic controls that allow users to pull new data and refresh analysis in real time.

The system is divided into Part A (core pipeline + static analysis) and Part B (dynamic update controls).

The initial database is seeded from the scraped and cleaned file llm_extend_applicant_data.json.

This file is loaded via load_data.py to the PostgreSQL database called gradcafe, table applicants.

The Flask dashboard triggers a background pipeline that scrapes, cleans, and loads new GradCafe records using scrape_update.py, clean_update.py, and load_update.py

The data is then analyzed using query_data.py.


⸻

Requirements

• Python 3.10 or newer
• PostgreSQL running locally

Python dependencies are listed in requirements.txt.

⸻

Dependencies Used

• Flask — web framework for the analysis dashboard
• psycopg — PostgreSQL database connectivity
• beautifulsoup4 — HTML parsing during scraping

All Python dependencies are listed in requirements.txt.

⸻

Setup and Run Instructions

	1.	Create and activate a virtual environment:

        	python3 -m venv .venv
        	source .venv/bin/activate

	2.	Install dependencies:

        	pip install -r requirements.txt

	3. Ensure PostgreSQL database exists:

        	createdb gradcafe

    	4. Create the applicants table inside the database:

        	psql gradcafe
		
        	Then run the SQL commands that create the applicants table required by this project.

⸻

━━━━━━━━━━━━━━━━━━━━
PART A — Core Pipeline + Static Analysis Dashboard
━━━━━━━━━━━━━━━━━━━━

Part A builds the dataset and displays analysis results through Flask.

⸻
Step A1 - Initial database seeding

File: load_data.py
Input: llm_extend_applicant_data.json 
Output: PostgreSQL database called gradcafe and a table called applicants

This script loads the Module 2 dataset (llm_extend_applicant_data.json) into the PostgreSQL database gradcafe, table applicants.  This step only needs to be run once to seed the database.

⸻

Step A2 — Scrape GradCafe Data

File: scrape_update.py
Output: applicant_data_update.json

This script scrapes GradCafe survey pages and associated detail pages to collect applicant records.

The scraper:

• Fetches survey pages sequentially
• Extracts applicant metadata
• Fetches result pages in parallel for GPA/GRE/degree information
• Deduplicates entries using URLs already stored in PostgreSQL
• Saves only newly discovered records

Run:

python scrape_update.py

⸻

Step A3 — Clean Raw Data

File: clean_update.py
Input: applicant_data_update.json
Output: cleaned_applicant_data_update.json

This step normalizes scraped data into a consistent schema.

Cleaning operations include:

• Removing HTML artifacts
• Normalizing whitespace
• Converting empty values to None
• Standardizing GPA/GRE values
• Mapping US/International status
• Ensuring all required fields exist

Run:

python clean_update.py

⸻

Step A4 — Load Data into PostgreSQL

File: load_update.py

This script inserts cleaned records into the PostgreSQL applicants table. All records are stored in the applicants table, which serves as the central dataset for analysis queries.

Features:

• Converts numeric/date fields
• Safely builds academic term strings
• Skips duplicate entries using URL conflict protection

Run:

python load_update.py

⸻

Step A5 — Static Flask Analysis Dashboard

Files:

app.py
query_data.py
templates/index.html
static/style.css

Flask displays analysis results using database queries.

query_data.py runs SQL queries to compute:

• Applicant counts
• GPA/GRE averages
• Acceptance statistics
• Program/university summaries

Run the web app:

python app.py

Open browser:

http://127.0.0.1:5000/analysis

This displays the static analysis dashboard.

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

Known Limitations

• Some GradCafe entries lack GPA/GRE or start-term data
• Occasional network timeouts may skip detail pages
• Missing fields are stored as None to preserve dataset consistency

⸻

Summary

This project implements:

• Web scraping pipeline
• Data normalization
• PostgreSQL integration
• Flask analytics dashboard
• Dynamic update controls

The result is a reproducible, database-backed analytics system that supports live updates through a browser interface.