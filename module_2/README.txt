Name: Navid Ziran
JHED ID: nziran1
Module Info: Module 2 — GradCafe Web Scraper + Data Cleaner + LLM Labeling
Due Date: Sunday, 2/01/2026

⸻

Approach

This assignment is implemented as a 4-step pipeline:

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
	•	regex (re) to parse decision strings like “Accepted on 29 Jan”
	•	de-duplication using a set of entry_url values to avoid duplicates
	•	periodic checkpoint saves to prevent data loss during long scrapes

⸻

Step 2 — Result-page detail scraping "(/result/)" with parallel processing

File: scrape.py
Output fields added into applicant_data.json
	•	Each row includes a detail page URL like:
        https://www.thegradcafe.com/result/<id>
	•	The scraper fetches these detail pages to extract additional fields required by the rubric, including:
	•	International / American student (from “Degree’s Country of Origin”)
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
        (ex: “GRE General:” incorrectly stored as a value).
	•	is_international is only set when the origin field is present.

⸻

Step 3 — clean_data(): Clean and structure output dataset

File: clean.py
Input: applicant_data.json
Output: cleaned_applicant_data.json

Cleaning steps:
	•	Remove any remaining HTML tags (defensive)
	•	Normalize whitespace
	•	Convert empty strings to None
	•	Ensure is_international is only True / False / None
	•	Ensure all required keys exist in every record
	•	Create a combined “program” field used for the LLM step:
        program = “<program_name_raw>, <university_raw>”

⸻

Step 4 — LLM processing (provided hosting package)

Folder: llm_hosting
Command used:
python app.py --file ../cleaned_applicant_data.json > out.json

This produces an output file containing additional LLM-generated labels.

⸻

Known Bugs / Limitations
	1.	Semester and Year of Program Start are not populated

	•	The rubric requests: “Semester and Year of Program Start (if available)”
	•	The scraper attempted to find “Term” and “Year” labels on result pages, but these fields were not present on the pages tested.
	•	Therefore start_term and start_year remain None across the dataset.

	2.	A small number of result pages may fail during scraping

	•	Due to timeouts or throttling, a small number of detail page fetches may fail.
	•	When this happens, the base survey record is still saved, but detail fields may remain None.
	•	A future improvement would be adding a re-try repair pass after scraping completes.