
# Project: CodeAlpha Web Scraper & Data Cleaning Pipeline
# Description: Scrapes book listings from 'Books to Scrape', handles pagination,
#              cleans the extracted dataset with pandas, and exports to CSV.

import time
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
import pandas as pd

# The starting URL of the bookstore catalog
BASE_URL = "http://books.toscrape.com/"

# Dictionary to convert word ratings into easy-to-use numbers
RATING_MAP = {
    "One": 1,
    "Two": 2,
    "Three": 3,
    "Four": 4,
    "Five": 5
}


def get_star_rating(card):
    """
    Extracts the star rating from the book card element.
    In the HTML, the class looks like: class="star-rating Three"
    """
    rating_tag = card.find("p", class_="star-rating")
    if rating_tag:
        # Get all classes on this paragraph (e.g. ['star-rating', 'Three'])
        classes = rating_tag.get("class", [])
        for c in classes:
            if c in RATING_MAP:
                return RATING_MAP[c]
    return None


def extract_book_details(card, page_url):
    """
    Extracts the title, price, rating, availability, and links for a single book card.
    """
    # 1. Book Title
    # Note: We look at the 'title' attribute on the <a> tag because the visible
    # text is sometimes shortened with an ellipsis like 'A Light in the...'
    title_tag = card.h3.find("a")
    if title_tag and title_tag.has_attr("title"):
        title = title_tag["title"]
    elif title_tag:
        title = title_tag.text.strip()
    else:
        title = "Unknown Title"

    # 2. Detail Page Link (converting relative link to full link)
    if title_tag and title_tag.has_attr("href"):
        book_link = urljoin(page_url, title_tag["href"])
    else:
        book_link = ""

    # 3. Price (raw text, e.g. "£51.77")
    price_tag = card.find("p", class_="price_color")
    price_raw = price_tag.text.strip() if price_tag else ""

    # 4. Rating (numeric 1 to 5)
    rating = get_star_rating(card)

    # 5. Availability (e.g. "In stock")
    stock_tag = card.find("p", class_="instock availability")
    stock_text = stock_tag.text.strip() if stock_tag else ""

    # 6. Book Cover Image URL
    img_tag = card.find("img")
    if img_tag and img_tag.has_attr("src"):
        image_url = urljoin(page_url, img_tag["src"])
    else:
        image_url = ""

    # Return as a clean dictionary
    return {
        "title": title,
        "price_raw": price_raw,
        "rating": rating,
        "availability": stock_text,
        "product_url": book_link,
        "image_url": image_url,
    }


def scrape_all_books(start_url=BASE_URL, max_pages=5, delay_seconds=0.5):
    """
    Visits pages one by one, grabs all books on each page,
    and follows the 'next' button until the limit is reached.
    """
    current_page_url = start_url
    scraped_books = []
    page_number = 1

    # Standard browser header so the request looks like a real browser
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    print("=" * 60)
    print(f"[*] Starting Web Scraper (Target: Up to {max_pages} pages)")
    print("=" * 60)

    while current_page_url and page_number <= max_pages:
        print(f"\n[Page {page_number}] Fetching: {current_page_url}")

        try:
            response = requests.get(current_page_url, headers=headers, timeout=10)
            response.raise_for_status()
        except requests.RequestException as error:
            print(f"[!] Error loading page: {error}")
            break

        # Parse HTML
        soup = BeautifulSoup(response.text, "html.parser")

        # Find all book cards on the current page
        book_cards = soup.find_all("article", class_="product_pod")
        print(f"    -> Found {len(book_cards)} books on this page.")

        # Extract info for each book
        for card in book_cards:
            book_info = extract_book_details(card, current_page_url)
            book_info["page_scraped"] = page_number
            scraped_books.append(book_info)

        # Check for the 'next' button in pagination
        next_button = soup.find("li", class_="next")
        if next_button and next_button.find("a"):
            next_href = next_button.find("a")["href"]
            current_page_url = urljoin(current_page_url, next_href)
            page_number += 1
        else:
            print("    -> No more pages found! Reached the end.")
            break

        # Polite delay to avoid hammering the website
        time.sleep(delay_seconds)

    print("\n" + "=" * 60)
    print(f"[+] Scraping completed! Total books collected: {len(scraped_books)}")
    print("=" * 60)

    return scraped_books


def clean_and_save_data(raw_data):
    """
    Converts the raw book records into a pandas DataFrame,
    cleans the formatting, and saves both raw and clean CSV files.
    """
    print("\n[*] Step 2: Cleaning and Validating Data with Pandas...")

    # Load records into a pandas DataFrame
    df = pd.DataFrame(raw_data)

    # Save the raw data first (good data practice!)
    df.to_csv("output_raw.csv", index=False, encoding="utf-8-sig")
    print("    -> Saved raw data to 'output_raw.csv'")

    # 1. Remove any duplicate books (based on title and URL)
    duplicates = df.duplicated(subset=["title", "product_url"]).sum()
    if duplicates > 0:
        print(f"    -> Found and removed {duplicates} duplicate entries.")
        df = df.drop_duplicates(subset=["title", "product_url"])

    # 2. Clean Price: remove the '£' symbol and convert text into a float number
    # e.g., '£51.77' becomes 51.77
    df["price_gbp"] = (
        df["price_raw"]
        .astype(str)
        .str.replace("£", "", regex=False)
        .str.replace("Â", "", regex=False)
        .str.strip()
    )
    df["price_gbp"] = pd.to_numeric(df["price_gbp"], errors="coerce")

    # 3. Clean Availability: clean whitespace and add a clear True/False flag
    df["in_stock"] = df["availability"].str.lower().str.contains("in stock", na=False)
    df["availability_clean"] = df["availability"].str.replace(r"\s+", " ", regex=True).str.strip()

    # 4. Organize columns in a clean, logical order
    clean_columns = [
        "title",
        "price_gbp",
        "rating",
        "in_stock",
        "availability_clean",
        "product_url",
        "image_url",
        "page_scraped"
    ]
    cleaned_df = df[clean_columns]

    # Save the final cleaned data
    cleaned_df.to_csv("output_cleaned.csv", index=False, encoding="utf-8-sig")
    print("    -> Saved clean dataset to 'output_cleaned.csv'")

    # Display a small summary preview
    print("\n[+] First 5 Cleaned Records Preview:")
    print("-" * 60)
    for idx, row in cleaned_df.head(5).iterrows():
        print(f"- Title: {row['title']}")
        print(f"  Price: GBP {row['price_gbp']:.2f} | Rating: {row['rating']}/5 | Stock: {row['availability_clean']}")
    print("-" * 60)

    return cleaned_df


def main():
    # 1. Scrape 5 pages (100 books total) with a 0.5s pause between pages
    books = scrape_all_books(start_url=BASE_URL, max_pages=5, delay_seconds=0.5)

    # 2. Clean data and export to CSV
    if books:
        clean_and_save_data(books)
        print("\nAll tasks finished successfully! Your files are ready for submission.")
    else:
        print("\n[!] No books were collected. Please check your internet connection.")


if __name__ == "__main__":
    main()
