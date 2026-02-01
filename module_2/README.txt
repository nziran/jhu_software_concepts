Name: Navid Ziran
JHED ID: nziran1
Module Info: Module 2 — GradCafe Web Scraper + Data Cleaner + LLM Labeling
Due Date: Sunday, 2/01/2026

SSH Repo URL: git@github.com:nziran/jhu_software_concepts.git

This project consists of web scraping thegradcafe.com to obtain ~ 31,000 student entries (records).  The script then cleans the data and processes it via a developer-provided LLM.  

Requirements:  Python 3.10 or newer

Tools used: beautifulsoup4 (bs4) for HTML parsing

Setup and Run Instructions:

1. Create and activate a virtual environment:
   	python3 -m venv .venv
	source .venv/bin/activate

2. Install dependencies:
   	pip install -r requirements.txt
	pip install -r llm_hosting/requirements.txt

3. Run the scraper:
	python scrape.py (data outputs to applicant_data.json)

4. Run the cleaner:
	python clean.py (data outputs to cleaned_applicant_data.json)

5. Run the LLM model (data outputs to llm_extend_applicant_data.json):
	python llm_hosting/app.py --file cleaned_applicant_data.json > llm_extend_applicant_data.json

⸻

Approach

This assignment is implemented as a 4-step pipeline:

⸻

Step 1 — scrape_data(): Scrape GradCafe survey pages

File: scrape.py
Output: applicant_data.json (RAW / uncleaned)
	•	The script scrapes GradCafe survey pages:
		https://www.thegradcafe.com/survey/?page=N
	•	Each page contains ~20 applicant rows.
	•	From the survey table, the scraper collects:
	•	Program Name
	•	University
	•	Comments (if available on list page)
	•	Date of information added (date posted)
	•	Applicant Status (Accepted/Rejected/Waitlisted/Interview/etc.)
	•	Acceptance date (if status = Accepted)
	•	Rejection date (if status = Rejected)
	•	URL link to applicant entry (entry_url)

Tools used:
	•	urllib.request (Request + urlopen) for HTTP fetching (rubric-required)
	•	BeautifulSoup (bs4) to parse HTML tables
	•	re (regular expressions) to parse decision strings like “Accepted on 29 Jan”
	•	de-duplication using a set of entry_url values to avoid duplicates
	•	periodic checkpoint saves to prevent data loss during long scrapes

⸻

Step 2 — Detail scraping phase (executed inside scrape.py) with parallel processing to decrease time

File: scrape.py
Output fields added into applicant_data.json
	•	Each row includes a detail page URL like:
		https://www.thegradcafe.com/result/
	•	The scraper fetches these detail pages to extract additional fields required by the rubric, including:
	•	International status (derived from “Degree’s Country of Origin”)
	•	GRE score (if available)
	•	GRE Verbal score (if available)
	•	GRE Analytical Writing score (if available)
	•	GPA (if available)
	•	Degree Type (if available)
	•	Masters or PhD bucket (degree_level)

Parallel processing:
	•	The scraper uses ThreadPoolExecutor to fetch result pages concurrently.
	•	This speeds up scraping because result-page requests are network-bound and benefit from parallel fetching.

Safety/accuracy logic:
	•	Numeric fields (GPA/GRE) are extracted using regex to avoid “label-as-value” errors
		(example: “GRE General:” incorrectly stored as a value).
	•	is_international is computed from the detail page when "Degree’s Country of Origin" is present; otherwise it remains None.

⸻

Step 3 — clean_data(): Clean and structure output dataset

File: clean.py
Input: applicant_data.json
Output: cleaned_applicant_data.json

Cleaning steps:
	•	Remove any remaining HTML tags (defensive)
	•	Normalize whitespace
	•	Convert empty strings to None
	•	Standardize international status into a categorical value:
	•	If is_international == True → International
	•	If is_international == False → American
	•	If missing/unknown → None
	•	Ensure all required keys exist in every record

⸻

Step 4 — LLM processing (provided hosting package)

Folder: llm_hosting
Command used (run from module_2):

python llm_hosting/app.py --file cleaned_applicant_data.json > llm_extend_applicant_data.json

Note: llm_hosting/app.py writes JSONL output first (one record per line), so after it finishes I convert the .jsonl file 
into the final JSON file (llm_extend_applicant_data.json).

This produces an output file containing additional LLM-generated labels:
llm_extend_applicant_data.json

⸻

Known Bugs / Limitations / Obstacles 

	1.	Data Cleaning Challenge: Start Term / Start Year (Messy + Often Missing)

	GradCafe entries frequently do not explicitly list the semester/term and year that a student will begin their program.
	Many student posts only contain language (usually in the Comments field) such as:

	•	“Spring intake”
	•	“Fall intake”
	•	“starting soon”
	•	“summer research in 2025” (not a program start term)
	•	“I'm accepted for Fall but applied for Spring” (ambiguous)

	Because of this, start_term and start_year cannot always be reliably extracted without introducing false positives.

	What my cleaner does to address this:

	•	clean.py attempts to infer start_term and start_year only when BOTH are clearly present in their Comments, such as:
	•	“Fall 2026 start”
	•	“I'm accepted for Summer 2025”
	•	“July 2026 start date” (mapped to an academic term)

	2.	A small number of result pages may fail during scraping

	•	Due to timeouts or throttling, a small number of detail page fetches may fail.
	•	When this happens, the base survey record is still saved, but detail fields may remain None.
	•	A future improvement would be adding a retry/repair pass after scraping completes.

	3. 	During early development, the US/International field was not being populated correctly (11 cases for me) because the scraper was not 
		consistently extracting the country-of-origin information from the GradCafe detail result pages (/result/<id>), 
		and in some cases the cleaning step received missing/empty values.

	Fix implemented:

	•	scrape.py now computes a raw boolean is_international during the detail-page scrape:
		•	False = American
		•	True = International
		•	None = Not available

	•	clean.py then converts this raw boolean into the required rubric output format: "American" or "International" (or None if unavailable)
	•	The raw dataset (applicant_data.json) remains reproducible/traceable while the cleaned dataset (cleaned_applicant_data.json) matches the final 				required schema.

	This resolved the prior issue where international status was missing or inconsistent in the cleaned output.

	4. LLM Input Bug and Fix

	During testing, the LLM was producing incorrect university outputs because the provided llm_hosting/app.py code expected a single combined input string under 		the key "program" (containing both program + university together).

	However, my cleaned dataset stores these as two separate fields:
		•	"program"
		•	"university"

	Fix implemented:
		•	I updated llm_hosting/app.py so the LLM receives a combined string built from both fields (ex: "program, university").
		•	This allowed the LLM to correctly standardize the program and university together and output consistent results in:
		•	llm-generated-program
		•	llm-generated-university

	This change ensured the LLM step correctly “sees” both values and prevents random university mismatches.
