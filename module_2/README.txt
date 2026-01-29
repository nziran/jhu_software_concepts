Name: Navid Ziran
JHED ID: nziran1
Module Info: Module 2 – Assignment: Web Scraping (Due Sunday 11:59pm)

Approach:
1) robots.txt compliance:
   - Visited https://www.thegradcafe.com/robots.txt in browser.
   - Verified /survey/ and /result/ pages are not disallowed for user agents.
   - Saved screenshots as robots_gradcafe_1.jpg and robots_gradcafe_2.jpg under module_2/.

2) Data scraping (scrape.py):
   - Uses urllib (Request + urlopen) for all HTTP requests.
   - Iterates GradCafe survey pages at:
       https://www.thegradcafe.com/survey/?page=N
   - Parses the HTML table with BeautifulSoup, extracting per-row:
       university_raw, program_name_raw, date_posted, applicant_status,
       accepted_date/rejected_date (when present), and entry_url (/result/<id>).
   - Saves output as applicant_data.json (JSON list of dicts).
   - Includes throttling (delay) and periodic checkpoint saving to avoid data loss.

3) Data fields:
   - Always captured from /survey/: program name, university, date posted, entry url, status, accept/reject date.
   - “If available” fields (GRE/GPA/degree/international/start term/year/comments) are present as keys in the JSON schema.
     These are populated in Part II using the provided local model pipeline under module_2/llm_hosting (see below).

4) Data size:
   - Scraped 31,000 records (>= 30,000 required) into module_2/applicant_data.json.

Part II – Cleaning (clean.py + llm_hosting):
- The assignment provides an LLM standardizer package. Per instructions, it should be placed under:
    module_2/llm_hosting/
- After installing llm_hosting requirements, run the standardizer on applicant_data.json to produce:
    llm_extend_applicant_data.json
- Original raw fields program_name_raw and university_raw are preserved for traceability.

Known Bugs / Limitations:
- Some “if available” fields are only present on /result/<id> pages and are filled in Part II (cleaning step).
- Site structure changes could affect parsing; the scraper saves page1.html for inspection/debugging.