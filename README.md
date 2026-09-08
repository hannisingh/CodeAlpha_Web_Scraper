# CodeAlpha Web Scraper Project

A robust Python web scraping and data processing pipeline built as part of the **CodeAlpha Internship Program**.

## 📌 Project Overview
This project extracts structured book listing data across multiple pages from [Books to Scrape](http://books.toscrape.com/), cleans and transforms the raw fields, and exports analysis-ready datasets.

---

## 🛠️ Features & Architecture
- **Compliance Check:** Verified `robots.txt` and terms of service before initiating scraping.
- **Robust Parsing:** Uses `requests` and `BeautifulSoup` to parse HTML DOM structures.
- **Pagination Handling:** Automatically traverses multi-page catalogs using dynamic `urljoin` URL resolution.
- **Polite Crawling:** Enforces a `0.5s` delay (`time.sleep`) between page requests to avoid server strain.
- **Data Validation & Cleaning:**
  - Removes duplicate entries based on unique item signatures.
  - Cleans price text into numeric `float` values.
  - Converts text ratings (`One` to `Five`) to numerical values (`1` to `5`).
  - Normalizes availability text and generates a boolean `is_in_stock` field.
- **CSV Export:** Exports both `output_raw.csv` and `output_cleaned.csv` using `pandas`.

---

## 📁 Repository Structure
```text
CodeAlpha_Web_Scraper/
├── full_scraper.py      # Main end-to-end scraper & data cleaner script
├── requirements.txt     # Project dependencies
├── output_raw.csv       # Raw extracted dataset
├── output_cleaned.csv   # Processed analysis-ready dataset
└── README.md            # Project documentation
```

---

## 🚀 Quick Start & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/hannisingh/CodeAlpha_Web_Scraper.git
cd CodeAlpha_Web_Scraper
```

### 2. Create Virtual Environment & Install Dependencies
```bash
python -m venv .venv
# On Windows:
.\.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Run the Scraper Pipeline
```bash
python full_scraper.py
```

---

## 📊 Sample Output Data (`output_cleaned.csv`)

| Title | Price (£) | Rating | In Stock | Availability | Product Link |
| :--- | :--- | :--- | :--- | :--- | :--- |
| A Light in the Attic | 51.77 | 3 | True | In stock | [Link](http://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html) |
| Tipping the Velvet | 53.74 | 1 | True | In stock | [Link](http://books.toscrape.com/catalogue/tipping-the-velvet_999/index.html) |
| Soumission | 50.10 | 1 | True | In stock | [Link](http://books.toscrape.com/catalogue/soumission_998/index.html) |

---

## 👤 Author & Acknowledgments
- **Developer:** CodeAlpha Intern
- **Mentor/Organization:** [CodeAlpha](https://www.linkedin.com/company/codealpha/)
